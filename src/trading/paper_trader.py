"""
FinClaw - Paper Trading Engine
Simulated live trading with async loop, risk checks, and performance tracking.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Callable, Optional, Protocol

from src.portfolio.tracker import PortfolioTracker
from src.trading.oms import Order, OrderManager, OrderResult

logger = logging.getLogger(__name__)


class Strategy(Protocol):
    """Protocol for strategies usable with PaperTrader."""
    def generate_signals(self, data: dict[str, Any]) -> list[dict[str, Any]]: ...


@dataclass
class PaperTradeConfig:
    """Configuration for paper trading sessions."""
    max_position_pct: float = 0.10       # max 10% in one ticker
    max_total_exposure: float = 0.95     # max 95% invested
    stop_loss_pct: float = 0.05          # 5% stop loss per position
    slippage_bps: float = 5.0            # 5 bps slippage
    commission_per_trade: float = 0.0    # flat commission
    log_interval: int = 10               # log every N iterations


class PaperTrader:
    """
    Paper trading engine — runs an async loop fetching data, generating
    signals, applying risk checks, and executing simulated orders.
    """

    def __init__(
        self,
        initial_capital: float,
        strategy: Strategy,
        config: dict[str, Any] | None = None,
        price_fetcher: Callable[..., Any] | None = None,
    ):
        cfg = config or {}
        self.config = PaperTradeConfig(**{k: v for k, v in cfg.items() if hasattr(PaperTradeConfig, k)})
        self.portfolio = PortfolioTracker(initial_capital)
        self.strategy = strategy
        self.oms = OrderManager()
        self.price_fetcher = price_fetcher
        self.running = False
        self._iteration = 0
        self._trade_log: list[dict[str, Any]] = []
        self._latest_prices: dict[str, float] = {}

    # ------------------------------------------------------------------
    # Core loop
    # ------------------------------------------------------------------

    async def start(self, tickers: list[str], interval_sec: int = 60) -> None:
        """Run the paper trading loop until stop() is called."""
        self.running = True
        logger.info("Paper trader started — tickers=%s interval=%ds", tickers, interval_sec)
        try:
            while self.running:
                await self._tick(tickers)
                self._iteration += 1
                await asyncio.sleep(interval_sec)
        except asyncio.CancelledError:
            logger.info("Paper trader cancelled")
        finally:
            self.running = False
            logger.info("Paper trader stopped after %d iterations", self._iteration)

    def stop(self) -> None:
        self.running = False

    # ------------------------------------------------------------------
    # Single iteration
    # ------------------------------------------------------------------

    async def _tick(self, tickers: list[str]) -> None:
        data = await self.fetch_latest(tickers)
        if not data:
            return

        signals = self.strategy.generate_signals(data)
        orders = self.risk_check(signals)

        for order in orders:
            result = self.execute(order)
            if result and result.status == "filled":
                self._record_trade(result, order)

        # Check stop/limit orders
        self.oms.check_stops_and_limits(self._latest_prices)

        if self._iteration % self.config.log_interval == 0:
            self.log_state()

    async def fetch_latest(self, tickers: list[str]) -> dict[str, Any]:
        """Fetch latest price data for tickers."""
        if self.price_fetcher:
            if asyncio.iscoroutinefunction(self.price_fetcher):
                data = await self.price_fetcher(tickers)
            else:
                data = self.price_fetcher(tickers)
            if isinstance(data, dict):
                # Extract prices
                for t in tickers:
                    if t in data and isinstance(data[t], (int, float)):
                        self._latest_prices[t] = float(data[t])
                    elif t in data and isinstance(data[t], dict) and "price" in data[t]:
                        self._latest_prices[t] = float(data[t]["price"])
            return data
        # Default: return latest known prices
        return {t: self._latest_prices.get(t, 0) for t in tickers}

    def risk_check(self, signals: list[dict[str, Any]]) -> list[Order]:
        """Apply risk filters and convert signals to orders."""
        orders: list[Order] = []
        total_value = self._portfolio_value()

        for sig in signals:
            ticker = sig.get("ticker", "")
            side = sig.get("side", "")
            quantity = sig.get("quantity", 0)
            price = sig.get("price", self._latest_prices.get(ticker, 0))
            order_type = sig.get("order_type", "market")

            if not ticker or not side or quantity <= 0:
                continue

            # Position size check
            if side == "buy":
                position_value = quantity * price
                if total_value > 0 and position_value / total_value > self.config.max_position_pct:
                    max_qty = (total_value * self.config.max_position_pct) / price
                    quantity = max(int(max_qty), 0)
                    if quantity <= 0:
                        continue

                # Total exposure check
                current_exposure = self._invested_value() / total_value if total_value > 0 else 0
                if current_exposure >= self.config.max_total_exposure:
                    continue

            # Apply slippage
            slippage = price * self.config.slippage_bps / 10000
            fill_price = price + slippage if side == "buy" else price - slippage

            orders.append(Order(
                ticker=ticker,
                side=side,
                order_type=order_type,
                quantity=quantity,
                limit_price=fill_price,
            ))

        return orders

    def execute(self, order: Order) -> OrderResult | None:
        """Execute an order through the OMS."""
        result = self.oms.submit_order(order)
        if result.status == "filled":
            today = date.today()
            price = result.filled_price or 0
            try:
                if order.side == "buy":
                    self.portfolio.buy(order.ticker, result.filled_quantity, price, today)
                elif order.side == "sell":
                    self.portfolio.sell(order.ticker, result.filled_quantity, price, today)
            except ValueError as e:
                logger.warning("Portfolio update failed: %s", e)
                return None
        return result

    def _record_trade(self, result: OrderResult, order: Order) -> None:
        self._trade_log.append({
            "time": datetime.now().isoformat(),
            "order_id": result.order_id,
            "ticker": order.ticker,
            "side": order.side,
            "quantity": result.filled_quantity,
            "price": result.filled_price,
            "iteration": self._iteration,
        })

    def log_state(self) -> None:
        total = self._portfolio_value()
        n_pos = len(self.portfolio.positions)
        logger.info(
            "Iteration %d | Value: $%.2f | Cash: $%.2f | Positions: %d | Trades: %d",
            self._iteration, total, self.portfolio.cash, n_pos, len(self._trade_log),
        )

    # ------------------------------------------------------------------
    # Performance & state
    # ------------------------------------------------------------------

    def get_performance(self) -> dict[str, Any]:
        """Get performance summary."""
        perf = self.portfolio.get_performance()
        perf["total_trades"] = len(self._trade_log)
        perf["iterations"] = self._iteration
        perf["open_orders"] = len(self.oms.get_open_orders())
        return perf

    def get_trade_log(self) -> list[dict[str, Any]]:
        return list(self._trade_log)

    def set_prices(self, prices: dict[str, float]) -> None:
        """Manually set prices (useful for testing)."""
        self._latest_prices.update(prices)

    def _portfolio_value(self) -> float:
        equity = sum(
            pos.shares * self._latest_prices.get(pos.ticker, pos.avg_cost)
            for pos in self.portfolio.positions.values()
        )
        return self.portfolio.cash + equity

    def _invested_value(self) -> float:
        return sum(
            pos.shares * self._latest_prices.get(pos.ticker, pos.avg_cost)
            for pos in self.portfolio.positions.values()
        )
