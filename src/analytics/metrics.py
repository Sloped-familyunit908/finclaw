"""
Performance Metrics
Sharpe, Sortino, Calmar, drawdown analysis, win rate, profit factor, expectancy,
monthly returns heatmap data.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from agents.backtester import BacktestResult, Trade


@dataclass
class DrawdownInfo:
    max_drawdown: float
    max_drawdown_duration_bars: int
    recovery_time_bars: Optional[int]  # None if never recovered
    current_drawdown: float
    drawdown_curve: list[float]


@dataclass
class TradeStats:
    total_trades: int
    win_rate: float
    profit_factor: float
    expectancy: float  # average $ per trade
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    avg_duration_hours: float
    max_consecutive_wins: int
    max_consecutive_losses: int


@dataclass
class MonthlyReturn:
    year: int
    month: int
    ret: float


class PerformanceMetrics:
    """Comprehensive performance analysis from a BacktestResult."""

    @staticmethod
    def sharpe(daily_returns: list[float], risk_free: float = 0.05) -> float:
        if len(daily_returns) < 2:
            return 0
        mean = sum(daily_returns) / len(daily_returns) * 252
        std = math.sqrt(sum((r - sum(daily_returns)/len(daily_returns))**2
                            for r in daily_returns) / (len(daily_returns)-1)) * math.sqrt(252)
        return (mean - risk_free) / max(std, 0.001)

    @staticmethod
    def sortino(daily_returns: list[float], risk_free: float = 0.05) -> float:
        if len(daily_returns) < 2:
            return 0
        mean = sum(daily_returns) / len(daily_returns) * 252
        down = [r for r in daily_returns if r < 0]
        if len(down) < 2:
            return 0
        down_dev = math.sqrt(sum(r**2 for r in down) / len(down)) * math.sqrt(252)
        return (mean - risk_free) / max(down_dev, 0.001)

    @staticmethod
    def calmar(annualized_return: float, max_drawdown: float) -> float:
        if max_drawdown == 0:
            return 0
        return annualized_return / max(abs(max_drawdown), 0.001)

    @staticmethod
    def drawdown_analysis(equity_curve: list[float]) -> DrawdownInfo:
        if not equity_curve:
            return DrawdownInfo(0, 0, None, 0, [])

        peak = equity_curve[0]
        max_dd = 0
        dd_curve = []
        dd_start = 0
        max_dd_dur = 0
        in_dd = False
        recovered = True

        for i, eq in enumerate(equity_curve):
            if eq >= peak:
                peak = eq
                if in_dd:
                    max_dd_dur = max(max_dd_dur, i - dd_start)
                    in_dd = False
            elif not in_dd:
                dd_start = i
                in_dd = True
            dd = (eq - peak) / peak if peak > 0 else 0
            dd_curve.append(dd)
            max_dd = min(max_dd, dd)

        current_dd = dd_curve[-1] if dd_curve else 0
        recovery = None
        # Find recovery time from worst drawdown
        worst_idx = dd_curve.index(max_dd) if max_dd in dd_curve else 0
        for j in range(worst_idx, len(dd_curve)):
            if dd_curve[j] >= 0:
                recovery = j - worst_idx
                break

        return DrawdownInfo(max_dd, max_dd_dur, recovery, current_dd, dd_curve)

    @staticmethod
    def trade_stats(trades: list[Trade]) -> TradeStats:
        if not trades:
            return TradeStats(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl <= 0]
        wr = len(wins) / len(trades)
        avg_w = sum(t.pnl_pct for t in wins) / max(len(wins), 1)
        avg_l = sum(t.pnl_pct for t in losses) / max(len(losses), 1)
        gp = sum(t.pnl for t in wins)
        gl = abs(sum(t.pnl for t in losses))
        pf = gp / max(gl, 0.01)
        expectancy = sum(t.pnl for t in trades) / len(trades)

        largest_w = max((t.pnl_pct for t in wins), default=0)
        largest_l = min((t.pnl_pct for t in losses), default=0)

        # Duration
        durs = []
        for t in trades:
            if isinstance(t.entry_time, datetime) and isinstance(t.exit_time, datetime):
                durs.append((t.exit_time - t.entry_time).total_seconds() / 3600)
        avg_dur = sum(durs) / max(len(durs), 1)

        # Consecutive wins/losses
        max_cw = max_cl = cw = cl = 0
        for t in trades:
            if t.pnl > 0:
                cw += 1; cl = 0
            else:
                cl += 1; cw = 0
            max_cw = max(max_cw, cw)
            max_cl = max(max_cl, cl)

        return TradeStats(
            total_trades=len(trades), win_rate=wr, profit_factor=pf,
            expectancy=expectancy, avg_win=avg_w, avg_loss=avg_l,
            largest_win=largest_w, largest_loss=largest_l,
            avg_duration_hours=avg_dur,
            max_consecutive_wins=max_cw, max_consecutive_losses=max_cl,
        )

    @staticmethod
    def monthly_returns(trades: list[Trade]) -> list[MonthlyReturn]:
        """Aggregate trades into monthly returns."""
        monthly: dict[tuple, float] = {}
        for t in trades:
            if isinstance(t.exit_time, datetime):
                key = (t.exit_time.year, t.exit_time.month)
                monthly[key] = monthly.get(key, 0) + t.pnl_pct
        return [MonthlyReturn(k[0], k[1], v) for k, v in sorted(monthly.items())]
