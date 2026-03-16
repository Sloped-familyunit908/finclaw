"""
Walk-Forward Analysis
Train on a rolling window, test on the next out-of-sample period, slide forward.
Prevents look-ahead bias and measures true out-of-sample performance.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable, Awaitable

from agents.backtester import BacktestResult


@dataclass
class WalkForwardWindow:
    """A single in-sample / out-of-sample window."""
    window_id: int
    train_start: int
    train_end: int
    test_start: int
    test_end: int
    train_result: Optional[BacktestResult] = None
    test_result: Optional[BacktestResult] = None


@dataclass
class WalkForwardReport:
    """Aggregated walk-forward results."""
    windows: list[WalkForwardWindow]
    oos_total_return: float  # compounded out-of-sample return
    oos_sharpe: float
    oos_max_drawdown: float
    oos_win_rate: float
    oos_total_trades: int
    robustness_ratio: float  # OOS sharpe / IS sharpe — >0.5 is good
    efficiency_ratio: float  # OOS return / IS return

    def summary(self) -> str:
        lines = [
            "=== Walk-Forward Analysis Report ===",
            f"Windows: {len(self.windows)}",
            f"OOS Compounded Return: {self.oos_total_return:+.2%}",
            f"OOS Sharpe: {self.oos_sharpe:.2f}",
            f"OOS Max Drawdown: {self.oos_max_drawdown:.2%}",
            f"OOS Win Rate: {self.oos_win_rate:.1%}",
            f"OOS Total Trades: {self.oos_total_trades}",
            f"Robustness Ratio (OOS/IS Sharpe): {self.robustness_ratio:.2f}",
            f"Efficiency Ratio (OOS/IS Return): {self.efficiency_ratio:.2f}",
        ]
        for w in self.windows:
            tr = w.test_result
            if tr:
                lines.append(
                    f"  Window {w.window_id}: "
                    f"Train[{w.train_start}-{w.train_end}] "
                    f"Test[{w.test_start}-{w.test_end}] "
                    f"Return={tr.total_return:+.2%} Sharpe={tr.sharpe_ratio:.2f}"
                )
        return "\n".join(lines)


class WalkForwardAnalyzer:
    """
    Rolling walk-forward backtester.
    
    Splits data into overlapping train/test windows:
      [--- train_0 ---][-- test_0 --]
                  [--- train_1 ---][-- test_1 --]
                              [--- train_2 ---][-- test_2 --]
    """

    def __init__(
        self,
        train_bars: int = 252,  # ~1 year
        test_bars: int = 63,    # ~1 quarter
        step_bars: int = 63,    # slide by 1 quarter
    ):
        self.train_bars = train_bars
        self.test_bars = test_bars
        self.step_bars = step_bars

    def _generate_windows(self, total_bars: int) -> list[WalkForwardWindow]:
        windows = []
        wid = 0
        start = 0
        while start + self.train_bars + self.test_bars <= total_bars:
            windows.append(WalkForwardWindow(
                window_id=wid,
                train_start=start,
                train_end=start + self.train_bars,
                test_start=start + self.train_bars,
                test_end=min(start + self.train_bars + self.test_bars, total_bars),
            ))
            wid += 1
            start += self.step_bars
        return windows

    async def run(
        self,
        asset: str,
        strategy_name: str,
        price_history: list[dict],
        backtester_factory: Callable,
    ) -> WalkForwardReport:
        """
        Run walk-forward analysis.
        
        backtester_factory: callable that returns a backtester instance (e.g. BacktesterV7).
        """
        total = len(price_history)
        windows = self._generate_windows(total)

        if not windows:
            raise ValueError(
                f"Not enough data ({total} bars) for walk-forward with "
                f"train={self.train_bars}, test={self.test_bars}"
            )

        is_sharpes = []
        oos_returns = []
        oos_sharpes = []
        oos_drawdowns = []
        oos_trades_total = 0
        oos_wins = 0
        oos_trades_count = 0

        for w in windows:
            bt = backtester_factory()

            # Train (in-sample)
            train_data = price_history[w.train_start:w.train_end]
            try:
                w.train_result = await bt.run(asset, strategy_name, train_data)
                is_sharpes.append(w.train_result.sharpe_ratio)
            except Exception:
                w.train_result = None

            # Test (out-of-sample)
            test_data = price_history[w.test_start:w.test_end]
            bt2 = backtester_factory()
            try:
                w.test_result = await bt2.run(asset, strategy_name, test_data)
                oos_returns.append(w.test_result.total_return)
                oos_sharpes.append(w.test_result.sharpe_ratio)
                oos_drawdowns.append(w.test_result.max_drawdown)
                oos_trades_total += w.test_result.total_trades
                oos_wins += w.test_result.winning_trades
                oos_trades_count += w.test_result.total_trades
            except Exception:
                w.test_result = None

        # Compound OOS returns
        compound = 1.0
        for r in oos_returns:
            compound *= (1 + r)
        oos_total = compound - 1

        avg_oos_sharpe = sum(oos_sharpes) / max(len(oos_sharpes), 1)
        avg_is_sharpe = sum(is_sharpes) / max(len(is_sharpes), 1)
        worst_dd = min(oos_drawdowns) if oos_drawdowns else 0
        oos_wr = oos_wins / max(oos_trades_count, 1)

        is_compound = 1.0
        for w in windows:
            if w.train_result:
                is_compound *= (1 + w.train_result.total_return)
        is_total = is_compound - 1

        return WalkForwardReport(
            windows=windows,
            oos_total_return=oos_total,
            oos_sharpe=avg_oos_sharpe,
            oos_max_drawdown=worst_dd,
            oos_win_rate=oos_wr,
            oos_total_trades=oos_trades_total,
            robustness_ratio=avg_oos_sharpe / max(abs(avg_is_sharpe), 0.001),
            efficiency_ratio=oos_total / max(abs(is_total), 0.001),
        )
