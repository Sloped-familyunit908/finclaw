"""
Evaluator — backtest a YAML DSL strategy and compute fitness scores.

Uses FinClaw's existing Strategy DSL and expression evaluator to run
a simplified backtest on OHLCV data, then returns risk-adjusted metrics.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from src.strategy.dsl import StrategyDSL
from src.strategy.expression import OHLCVData


@dataclass
class FitnessScore:
    """Composite fitness score for a strategy backtest."""

    sharpe_ratio: float = 0.0
    total_return: float = 0.0
    max_drawdown: float = 0.0  # Always <= 0
    win_rate: float = 0.0
    total_trades: int = 0

    # -- Weights for composite score --
    _SHARPE_W: float = field(default=0.40, repr=False, compare=False)
    _RETURN_W: float = field(default=0.25, repr=False, compare=False)
    _DRAWDOWN_W: float = field(default=0.20, repr=False, compare=False)
    _WINRATE_W: float = field(default=0.15, repr=False, compare=False)

    def composite(self) -> float:
        """Single comparable score combining all metrics.

        Higher is better.  A strategy with zero trades gets a penalty.
        """
        if self.total_trades == 0:
            return -1.0

        # Normalise components into roughly [−1, 1] ranges
        sharpe_component = min(self.sharpe_ratio, 5.0) / 5.0  # cap at 5
        return_component = max(min(self.total_return, 2.0), -1.0)  # clamp
        drawdown_component = 1.0 + self.max_drawdown  # dd = −0.3 → 0.7
        winrate_component = self.win_rate  # already 0–1

        return (
            self._SHARPE_W * sharpe_component
            + self._RETURN_W * return_component
            + self._DRAWDOWN_W * drawdown_component
            + self._WINRATE_W * winrate_component
        )

    # -- comparison helpers --
    def __gt__(self, other: "FitnessScore") -> bool:
        return self.composite() > other.composite()

    def __lt__(self, other: "FitnessScore") -> bool:
        return self.composite() < other.composite()

    def __ge__(self, other: "FitnessScore") -> bool:
        return self.composite() >= other.composite()

    def __le__(self, other: "FitnessScore") -> bool:
        return self.composite() <= other.composite()

    def to_dict(self) -> dict[str, Any]:
        return {
            "sharpe_ratio": self.sharpe_ratio,
            "total_return": self.total_return,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "total_trades": self.total_trades,
            "composite": self.composite(),
        }


class Evaluator:
    """Evaluate a YAML strategy on historical OHLCV data.

    Uses a simplified bar-by-bar backtest (long-only) to produce
    a :class:`FitnessScore`.
    """

    def __init__(self) -> None:
        self._dsl = StrategyDSL()
        self._last_feedback: dict[str, Any] | None = None

    # -- public API --

    @property
    def last_feedback(self) -> dict[str, Any] | None:
        """Detailed feedback from the most recent evaluation."""
        return self._last_feedback

    def evaluate(self, strategy_yaml: str, data: OHLCVData) -> FitnessScore:
        """Backtest *strategy_yaml* against *data* and return a fitness score."""
        strategy = self._dsl.parse(strategy_yaml)
        trades = self._simulate(strategy, data)
        score = self._compute_score(trades, data)

        self._last_feedback = {
            "score": score.to_dict(),
            "trade_count": score.total_trades,
            "winning_trades": sum(1 for t in trades if t["pnl"] > 0),
            "losing_trades": sum(1 for t in trades if t["pnl"] <= 0),
            "avg_win": float(np.mean([t["pnl"] for t in trades if t["pnl"] > 0])) if any(t["pnl"] > 0 for t in trades) else 0.0,
            "avg_loss": float(np.mean([t["pnl"] for t in trades if t["pnl"] <= 0])) if any(t["pnl"] <= 0 for t in trades) else 0.0,
            "periods": len(data.close),
        }
        return score

    # -- internals --

    def _simulate(self, strategy: Any, data: OHLCVData) -> list[dict[str, Any]]:
        """Bar-by-bar long-only backtest."""
        trades: list[dict[str, Any]] = []
        n = len(data.close)
        in_position = False
        entry_price = 0.0
        entry_index = 0

        # Need at least some bars for indicators to warm up
        warmup = 60
        for i in range(warmup, n):
            if not in_position:
                try:
                    if strategy.should_enter(data, i):
                        in_position = True
                        entry_price = float(data.close[i])
                        entry_index = i
                except Exception:
                    continue
            else:
                exit_triggered = False
                try:
                    exit_triggered = strategy.should_exit(data, i)
                except Exception:
                    pass

                # Check risk limits
                current_price = float(data.close[i])
                pnl_pct = (current_price - entry_price) / entry_price

                if strategy.risk.stop_loss and pnl_pct <= -strategy.risk.stop_loss:
                    exit_triggered = True
                if strategy.risk.take_profit and pnl_pct >= strategy.risk.take_profit:
                    exit_triggered = True

                if exit_triggered:
                    trades.append({
                        "entry_index": entry_index,
                        "exit_index": i,
                        "entry_price": entry_price,
                        "exit_price": current_price,
                        "pnl": pnl_pct,
                        "bars_held": i - entry_index,
                    })
                    in_position = False

        # Close open position at end
        if in_position:
            final = float(data.close[-1])
            trades.append({
                "entry_index": entry_index,
                "exit_index": n - 1,
                "entry_price": entry_price,
                "exit_price": final,
                "pnl": (final - entry_price) / entry_price,
                "bars_held": n - 1 - entry_index,
            })

        return trades

    def _compute_score(self, trades: list[dict[str, Any]], data: OHLCVData) -> FitnessScore:
        """Compute fitness metrics from trade list."""
        if not trades:
            return FitnessScore(
                sharpe_ratio=0.0,
                total_return=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                total_trades=0,
            )

        pnls = [t["pnl"] for t in trades]
        total_return = float(np.prod([1 + p for p in pnls]) - 1)
        win_rate = sum(1 for p in pnls if p > 0) / len(pnls)

        # Sharpe Ratio (annualised, approximate)
        avg_bars = float(np.mean([t["bars_held"] for t in trades]))
        trades_per_year = 252 / max(avg_bars, 1)
        mean_pnl = float(np.mean(pnls))
        std_pnl = float(np.std(pnls, ddof=1)) if len(pnls) > 1 else 1e-9
        sharpe = (mean_pnl / max(std_pnl, 1e-9)) * math.sqrt(trades_per_year)
        if not math.isfinite(sharpe):
            sharpe = 0.0

        # Max drawdown from equity curve
        equity = [1.0]
        for p in pnls:
            equity.append(equity[-1] * (1 + p))
        peak = equity[0]
        max_dd = 0.0
        for e in equity:
            if e > peak:
                peak = e
            dd = (e - peak) / peak
            if dd < max_dd:
                max_dd = dd

        return FitnessScore(
            sharpe_ratio=sharpe,
            total_return=total_return,
            max_drawdown=max_dd,
            win_rate=win_rate,
            total_trades=len(trades),
        )
