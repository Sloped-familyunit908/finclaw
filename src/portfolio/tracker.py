"""Portfolio Tracker — track positions, cash, and performance over time."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable


@dataclass
class Position:
    """A single holding."""
    ticker: str
    shares: float
    avg_cost: float
    entry_date: date


@dataclass
class Snapshot:
    """Daily portfolio snapshot."""
    date: date
    positions: dict[str, Position]
    cash: float
    total_value: float


class PortfolioTracker:
    """Track a portfolio over time with buy/sell/snapshot/performance."""

    def __init__(self, initial_capital: float = 100_000.0):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: dict[str, Position] = {}
        self.history: list[Snapshot] = []
        self.transactions: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    def buy(self, ticker: str, shares: float, price: float, dt: date) -> None:
        """Buy *shares* of *ticker* at *price* on *dt*."""
        cost = shares * price
        if cost > self.cash:
            raise ValueError(f"Insufficient cash: need {cost:.2f}, have {self.cash:.2f}")
        self.cash -= cost
        if ticker in self.positions:
            pos = self.positions[ticker]
            total_shares = pos.shares + shares
            pos.avg_cost = (pos.avg_cost * pos.shares + price * shares) / total_shares
            pos.shares = total_shares
        else:
            self.positions[ticker] = Position(ticker=ticker, shares=shares, avg_cost=price, entry_date=dt)
        self.transactions.append({"type": "buy", "ticker": ticker, "shares": shares, "price": price, "date": dt})

    def sell(self, ticker: str, shares: float, price: float, dt: date) -> None:
        """Sell *shares* of *ticker* at *price* on *dt*."""
        if ticker not in self.positions or self.positions[ticker].shares < shares:
            raise ValueError(f"Insufficient shares for {ticker}")
        pos = self.positions[ticker]
        self.cash += shares * price
        pos.shares -= shares
        if pos.shares <= 0:
            del self.positions[ticker]
        self.transactions.append({"type": "sell", "ticker": ticker, "shares": shares, "price": price, "date": dt})

    def snapshot(self, dt: date, prices: dict[str, float]) -> Snapshot:
        """Record a daily snapshot given current *prices*."""
        equity = sum(pos.shares * prices.get(pos.ticker, pos.avg_cost) for pos in self.positions.values())
        total = self.cash + equity
        snap = Snapshot(
            date=dt,
            positions={t: Position(p.ticker, p.shares, p.avg_cost, p.entry_date) for t, p in self.positions.items()},
            cash=self.cash,
            total_value=total,
        )
        self.history.append(snap)
        return snap

    def get_performance(self) -> dict[str, Any]:
        """Return summary performance metrics from snapshot history."""
        if not self.history:
            return {"error": "no snapshots"}
        values = [s.total_value for s in self.history]
        total_return = (values[-1] / self.initial_capital) - 1.0
        peak = values[0]
        max_dd = 0.0
        for v in values:
            if v > peak:
                peak = v
            dd = (peak - v) / peak
            if dd > max_dd:
                max_dd = dd
        # Daily returns
        daily_returns = [(values[i] / values[i - 1]) - 1.0 for i in range(1, len(values))]
        avg_daily = sum(daily_returns) / len(daily_returns) if daily_returns else 0.0
        import math
        std_daily = (sum((r - avg_daily) ** 2 for r in daily_returns) / max(len(daily_returns) - 1, 1)) ** 0.5 if daily_returns else 0.0
        sharpe = (avg_daily / std_daily * math.sqrt(252)) if std_daily > 0 else 0.0
        return {
            "total_return": total_return,
            "max_drawdown": max_dd,
            "sharpe_ratio": sharpe,
            "num_snapshots": len(self.history),
            "start_date": self.history[0].date,
            "end_date": self.history[-1].date,
            "final_value": values[-1],
        }
