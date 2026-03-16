"""
FinClaw - Live Trading Engine
Async engine that connects to real exchanges, runs strategies,
and manages orders with integrated risk management.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Optional, Protocol

from src.exchanges.base import ExchangeAdapter
from src.events.event_bus import EventBus, TRADE_EXECUTED, SIGNAL_GENERATED
from src.trading.oms import Order, OrderManager, OrderResult

logger = logging.getLogger(__name__)


class TradingStrategy(Protocol):
    """Protocol for strategies compatible with the live engine."""

    def generate_signals(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        ...


class LiveTradingEngine:
    """
    Async live trading engine.

    Connects to an exchange adapter, runs a strategy on each tick,
    applies risk checks, and executes orders through the OMS.
    """

    def __init__(
        self,
        exchange: ExchangeAdapter,
        strategy: TradingStrategy,
        risk_manager=None,
        *,
        tickers: list[str] | None = None,
        tick_interval: float = 60.0,
        event_bus: EventBus | None = None,
    ):
        self.exchange = exchange
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.tickers = tickers or []
        self.tick_interval = tick_interval

        self.event_bus = event_bus or EventBus()
        self.oms = OrderManager(event_bus=self.event_bus)

        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self._iteration = 0
        self._start_time: Optional[float] = None

        # Tracking
        self._positions: dict[str, dict[str, Any]] = {}
        self._pnl: float = 0.0
        self._trade_count: int = 0
        self._errors: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the live trading loop."""
        if self.is_running:
            logger.warning("Engine already running")
            return

        self.is_running = True
        self._start_time = time.time()
        logger.info(
            "Live engine started — exchange=%s tickers=%s interval=%.1fs",
            self.exchange.name, self.tickers, self.tick_interval,
        )
        try:
            while self.is_running:
                await self._run_tick()
                self._iteration += 1
                await asyncio.sleep(self.tick_interval)
        except asyncio.CancelledError:
            logger.info("Live engine cancelled")
        except Exception as exc:
            self._errors.append({"time": datetime.now().isoformat(), "error": str(exc)})
            logger.exception("Live engine error: %s", exc)
        finally:
            self.is_running = False
            logger.info("Live engine stopped after %d ticks", self._iteration)

    async def stop(self) -> None:
        """Gracefully stop the engine."""
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Live engine stop requested")

    def start_background(self) -> asyncio.Task:
        """Start engine as a background task."""
        self._task = asyncio.get_event_loop().create_task(self.start())
        return self._task

    # ------------------------------------------------------------------
    # Tick processing
    # ------------------------------------------------------------------

    async def on_tick(self, data: dict[str, Any]) -> list[OrderResult]:
        """
        Process a single tick of market data.
        Can be called externally for event-driven architectures.
        """
        results: list[OrderResult] = []

        # Generate signals
        try:
            signals = self.strategy.generate_signals(data)
        except Exception as exc:
            logger.error("Strategy error: %s", exc)
            self._errors.append({"time": datetime.now().isoformat(), "error": f"strategy: {exc}"})
            return results

        if signals:
            self.event_bus.publish(SIGNAL_GENERATED, {"signals": signals}, source="live_engine")

        # Process each signal
        for signal in signals:
            order = self._signal_to_order(signal)
            if order is None:
                continue

            # Risk check
            if self.risk_manager:
                risk_result = self.risk_manager.check_order(order, self._get_portfolio_snapshot())
                if not risk_result.approved:
                    logger.warning("Risk rejected order: %s — %s", order.order_id, risk_result.reason)
                    continue

            # Execute
            result = self.oms.submit_order(order)
            results.append(result)

            if result.status == "filled":
                self._update_position(order, result)
                self._trade_count += 1

        # Check pending stop/limit orders
        prices = self._extract_prices(data)
        if prices:
            triggered = self.oms.check_stops_and_limits(prices)
            results.extend(triggered)

        return results

    async def _run_tick(self) -> None:
        """Fetch data from exchange and process a tick."""
        data: dict[str, Any] = {}
        for ticker in self.tickers:
            try:
                ticker_data = self.exchange.get_ticker(ticker)
                data[ticker] = ticker_data
            except Exception as exc:
                logger.error("Failed to fetch %s: %s", ticker, exc)
                self._errors.append({
                    "time": datetime.now().isoformat(),
                    "error": f"fetch {ticker}: {exc}",
                })

        if data:
            await self.on_tick(data)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _signal_to_order(self, signal: dict[str, Any]) -> Order | None:
        """Convert a strategy signal dict to an Order."""
        ticker = signal.get("ticker", "")
        side = signal.get("side", "")
        quantity = signal.get("quantity", 0)

        if not ticker or not side or quantity <= 0:
            return None

        return Order(
            ticker=ticker,
            side=side,
            order_type=signal.get("order_type", "market"),
            quantity=quantity,
            limit_price=signal.get("price"),
            stop_price=signal.get("stop_price"),
        )

    def _extract_prices(self, data: dict[str, Any]) -> dict[str, float]:
        """Extract last prices from tick data."""
        prices: dict[str, float] = {}
        for ticker, info in data.items():
            if isinstance(info, (int, float)):
                prices[ticker] = float(info)
            elif isinstance(info, dict):
                price = info.get("last") or info.get("price") or info.get("close")
                if price is not None:
                    prices[ticker] = float(price)
        return prices

    def _update_position(self, order: Order, result: OrderResult) -> None:
        """Update internal position tracking after a fill."""
        ticker = order.ticker
        price = result.filled_price or 0
        qty = result.filled_quantity

        if ticker not in self._positions:
            self._positions[ticker] = {"quantity": 0, "avg_price": 0, "realized_pnl": 0}

        pos = self._positions[ticker]
        if order.side == "buy":
            total_cost = pos["quantity"] * pos["avg_price"] + qty * price
            pos["quantity"] += qty
            pos["avg_price"] = total_cost / pos["quantity"] if pos["quantity"] else 0
        elif order.side == "sell":
            if pos["quantity"] > 0:
                pnl = (price - pos["avg_price"]) * min(qty, pos["quantity"])
                pos["realized_pnl"] += pnl
                self._pnl += pnl
            pos["quantity"] = max(0, pos["quantity"] - qty)

    def _get_portfolio_snapshot(self) -> dict[str, Any]:
        """Return current portfolio state for risk checks."""
        return {
            "positions": dict(self._positions),
            "open_orders": len(self.oms.get_open_orders()),
            "pnl": self._pnl,
            "trade_count": self._trade_count,
        }

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> dict[str, Any]:
        """Return engine status: PnL, positions, orders, uptime."""
        uptime = time.time() - self._start_time if self._start_time else 0
        return {
            "is_running": self.is_running,
            "exchange": self.exchange.name,
            "tickers": self.tickers,
            "uptime_seconds": round(uptime, 1),
            "iterations": self._iteration,
            "pnl": round(self._pnl, 2),
            "positions": {
                t: {
                    "quantity": p["quantity"],
                    "avg_price": round(p["avg_price"], 4),
                    "realized_pnl": round(p["realized_pnl"], 2),
                }
                for t, p in self._positions.items()
                if p["quantity"] > 0
            },
            "open_orders": len(self.oms.get_open_orders()),
            "total_trades": self._trade_count,
            "errors": len(self._errors),
            "last_errors": self._errors[-3:] if self._errors else [],
        }
