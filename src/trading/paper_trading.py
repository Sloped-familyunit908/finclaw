"""
FinClaw - Paper Trading Engine (v2)
Extends LiveTradingEngine with simulated fills, virtual balance,
and detailed performance tracking.
"""

from __future__ import annotations

import math
import time
from datetime import datetime
from typing import Any, Optional

from src.exchanges.base import ExchangeAdapter
from src.events.event_bus import EventBus
from src.trading.live_engine import LiveTradingEngine, TradingStrategy
from src.trading.oms import Order, OrderResult

import logging

logger = logging.getLogger(__name__)


class PaperTradingEngine(LiveTradingEngine):
    """
    Paper trading engine — same interface as LiveTradingEngine but
    executes against simulated fills with virtual balance tracking.
    """

    def __init__(
        self,
        exchange: ExchangeAdapter,
        strategy: TradingStrategy,
        *,
        initial_capital: float = 100_000.0,
        risk_manager=None,
        tickers: list[str] | None = None,
        tick_interval: float = 60.0,
        slippage_bps: float = 5.0,
        commission_rate: float = 0.001,
        event_bus: EventBus | None = None,
    ):
        super().__init__(
            exchange=exchange,
            strategy=strategy,
            risk_manager=risk_manager,
            tickers=tickers,
            tick_interval=tick_interval,
            event_bus=event_bus,
        )
        self.initial_capital = initial_capital
        self.virtual_balance = initial_capital
        self.virtual_positions: dict[str, dict[str, Any]] = {}
        self.trade_history: list[dict[str, Any]] = []
        self.slippage_bps = slippage_bps
        self.commission_rate = commission_rate
        self._equity_curve: list[dict[str, Any]] = []
        self._peak_equity: float = initial_capital
        self._max_drawdown: float = 0.0

    # ------------------------------------------------------------------
    # Override order execution for paper trading
    # ------------------------------------------------------------------

    async def on_tick(self, data: dict[str, Any]) -> list[OrderResult]:
        """Process tick with paper execution."""
        results = await super().on_tick(data)

        # Record equity snapshot
        prices = self._extract_prices(data)
        equity = self._calculate_equity(prices)
        self._equity_curve.append({
            "time": datetime.now().isoformat(),
            "equity": equity,
            "cash": self.virtual_balance,
            "iteration": self._iteration,
        })

        # Track drawdown
        if equity > self._peak_equity:
            self._peak_equity = equity
        if self._peak_equity > 0:
            dd = (self._peak_equity - equity) / self._peak_equity
            self._max_drawdown = max(self._max_drawdown, dd)

        return results

    def _update_position(self, order: Order, result: OrderResult) -> None:
        """Override to track virtual balance and paper positions."""
        super()._update_position(order, result)

        price = result.filled_price or 0
        qty = result.filled_quantity
        slippage = price * self.slippage_bps / 10_000
        commission = price * qty * self.commission_rate

        if order.side == "buy":
            effective_price = price + slippage
            cost = effective_price * qty + commission
            self.virtual_balance -= cost

            if order.ticker not in self.virtual_positions:
                self.virtual_positions[order.ticker] = {
                    "quantity": 0, "avg_price": 0, "entry_time": datetime.now().isoformat()
                }
            pos = self.virtual_positions[order.ticker]
            total_cost = pos["quantity"] * pos["avg_price"] + qty * effective_price
            pos["quantity"] += qty
            pos["avg_price"] = total_cost / pos["quantity"] if pos["quantity"] else 0

        elif order.side == "sell":
            effective_price = price - slippage
            revenue = effective_price * qty - commission
            self.virtual_balance += revenue

            if order.ticker in self.virtual_positions:
                pos = self.virtual_positions[order.ticker]
                pos["quantity"] = max(0, pos["quantity"] - qty)
                if pos["quantity"] == 0:
                    del self.virtual_positions[order.ticker]

        self.trade_history.append({
            "time": datetime.now().isoformat(),
            "order_id": result.order_id,
            "ticker": order.ticker,
            "side": order.side,
            "quantity": qty,
            "price": price,
            "effective_price": effective_price,
            "commission": round(commission, 4),
            "balance_after": round(self.virtual_balance, 2),
        })

    # ------------------------------------------------------------------
    # Performance
    # ------------------------------------------------------------------

    def _calculate_equity(self, prices: dict[str, float] | None = None) -> float:
        """Calculate total equity (cash + positions)."""
        prices = prices or {}
        position_value = sum(
            p["quantity"] * prices.get(ticker, p["avg_price"])
            for ticker, p in self.virtual_positions.items()
        )
        return self.virtual_balance + position_value

    def get_performance(self) -> dict[str, Any]:
        """
        Get detailed performance metrics:
        Sharpe ratio, max drawdown, total PnL, win rate, etc.
        """
        equity = self._calculate_equity()
        total_pnl = equity - self.initial_capital
        pnl_pct = (total_pnl / self.initial_capital * 100) if self.initial_capital else 0

        # Win rate
        wins = sum(1 for t in self.trade_history if t["side"] == "sell" and t.get("effective_price", 0) > 0)
        sells = sum(1 for t in self.trade_history if t["side"] == "sell")
        win_rate = (wins / sells * 100) if sells else 0

        # Sharpe ratio from equity curve
        sharpe = self._calculate_sharpe()

        # Total commissions
        total_commission = sum(t.get("commission", 0) for t in self.trade_history)

        return {
            "initial_capital": self.initial_capital,
            "current_equity": round(equity, 2),
            "cash": round(self.virtual_balance, 2),
            "total_pnl": round(total_pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "max_drawdown_pct": round(self._max_drawdown * 100, 2),
            "sharpe_ratio": round(sharpe, 4),
            "total_trades": len(self.trade_history),
            "win_rate": round(win_rate, 1),
            "total_commission": round(total_commission, 2),
            "positions": {
                t: {"qty": p["quantity"], "avg_price": round(p["avg_price"], 4)}
                for t, p in self.virtual_positions.items()
            },
            "iterations": self._iteration,
        }

    def _calculate_sharpe(self, risk_free_rate: float = 0.0) -> float:
        """Calculate annualized Sharpe ratio from equity curve."""
        if len(self._equity_curve) < 2:
            return 0.0

        returns = []
        for i in range(1, len(self._equity_curve)):
            prev = self._equity_curve[i - 1]["equity"]
            curr = self._equity_curve[i]["equity"]
            if prev > 0:
                returns.append((curr - prev) / prev)

        if not returns:
            return 0.0

        mean_ret = sum(returns) / len(returns)
        if len(returns) < 2:
            return 0.0

        variance = sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1)
        std_ret = math.sqrt(variance)

        if std_ret == 0:
            return 0.0

        # Annualize (assume ~252 trading days)
        sharpe = (mean_ret - risk_free_rate) / std_ret * math.sqrt(252)
        return sharpe

    def get_status(self) -> dict[str, Any]:
        """Override to include paper trading details."""
        base = super().get_status()
        base["mode"] = "paper"
        base["virtual_balance"] = round(self.virtual_balance, 2)
        base["equity"] = round(self._calculate_equity(), 2)
        base["initial_capital"] = self.initial_capital
        base["max_drawdown_pct"] = round(self._max_drawdown * 100, 2)
        base["trade_history_count"] = len(self.trade_history)
        return base
