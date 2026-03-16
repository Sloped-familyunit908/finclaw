"""
Strategy Optimizer — grid search over YAML strategy parameters.

Usage:
    optimizer = StrategyOptimizer()
    results = optimizer.grid_search(
        strategy_yaml="...",
        params={"rsi_period": [10, 14, 20, 30], "sma_fast": [10, 20, 30]},
        data=ohlcv_data,
    )
    best = optimizer.best_params()
"""

from __future__ import annotations

import itertools
import re
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .dsl import StrategyDSL, Strategy
from .expression import OHLCVData


@dataclass
class OptimizationResult:
    """Result of a single parameter combination."""
    params: dict[str, Any]
    total_trades: int = 0
    winning_trades: int = 0
    win_rate: float = 0.0
    total_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    score: float = 0.0  # composite metric for ranking


class StrategyOptimizer:
    """Grid search optimizer for YAML strategy parameters."""

    def __init__(self) -> None:
        self._results: list[OptimizationResult] = []
        self._dsl = StrategyDSL()

    def grid_search(
        self,
        strategy_yaml: str,
        params: dict[str, list[Any]],
        data: OHLCVData,
    ) -> list[OptimizationResult]:
        """Run grid search over all parameter combinations.

        Args:
            strategy_yaml: Base YAML strategy with placeholder values
            params: Dict of param_name → list of values to try
            data: OHLCV data to backtest against

        Returns:
            List of OptimizationResult sorted by score (descending)
        """
        self._results.clear()
        keys = list(params.keys())
        value_lists = [params[k] for k in keys]

        for combo in itertools.product(*value_lists):
            param_dict = dict(zip(keys, combo))
            modified_yaml = self._substitute_params(strategy_yaml, param_dict)
            try:
                strategy = self._dsl.parse(modified_yaml)
            except ValueError:
                continue
            result = self._evaluate_strategy(strategy, data, param_dict)
            self._results.append(result)

        self._results.sort(key=lambda r: r.score, reverse=True)
        return self._results

    def best_params(self) -> dict[str, Any]:
        """Return parameters of the best-performing combination."""
        if not self._results:
            return {}
        return dict(self._results[0].params)

    def top_n(self, n: int = 5) -> list[OptimizationResult]:
        """Return top N results."""
        return self._results[:n]

    def _substitute_params(self, yaml_str: str, params: dict[str, Any]) -> str:
        """Replace parameter references in YAML expressions.

        Supports both {param_name} placeholders and direct number substitution
        in function calls like sma({sma_fast}) or rsi({rsi_period}).
        """
        result = yaml_str
        for key, value in params.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result

    def _evaluate_strategy(
        self, strategy: Strategy, data: OHLCVData, params: dict[str, Any]
    ) -> OptimizationResult:
        """Simple backtest evaluation of a strategy on OHLCV data."""
        n = len(data.close)
        if n < 60:
            return OptimizationResult(params=params)

        in_position = False
        entry_price = 0.0
        trades: list[float] = []  # return per trade
        equity = [1.0]

        # Start from bar 50 to ensure enough lookback
        for i in range(50, n):
            if not in_position:
                if strategy.should_enter(data, i):
                    in_position = True
                    entry_price = data.close[i]
            else:
                ret = (data.close[i] - entry_price) / entry_price
                # Check stop loss / take profit
                if strategy.risk.stop_loss and ret <= -strategy.risk.stop_loss:
                    trades.append(-strategy.risk.stop_loss)
                    in_position = False
                elif strategy.risk.take_profit and ret >= strategy.risk.take_profit:
                    trades.append(strategy.risk.take_profit)
                    in_position = False
                elif strategy.should_exit(data, i):
                    trades.append(ret)
                    in_position = False

                equity.append(equity[-1] * (1 + (trades[-1] if not in_position and trades else 0)))

        # Close any open position
        if in_position and entry_price > 0:
            ret = (data.close[-1] - entry_price) / entry_price
            trades.append(ret)

        total_trades = len(trades)
        winning = sum(1 for t in trades if t > 0)
        win_rate = winning / total_trades if total_trades > 0 else 0.0
        total_return = sum(trades) if trades else 0.0

        # Max drawdown
        equity_arr = np.array(equity)
        running_max = np.maximum.accumulate(equity_arr)
        drawdowns = (equity_arr - running_max) / np.where(running_max > 0, running_max, 1)
        max_dd = float(np.min(drawdowns)) if len(drawdowns) > 0 else 0.0

        # Sharpe ratio (simplified)
        if trades:
            mean_ret = np.mean(trades)
            std_ret = np.std(trades)
            sharpe = float(mean_ret / std_ret * np.sqrt(252)) if std_ret > 0 else 0.0
        else:
            sharpe = 0.0

        # Composite score: weighted combination
        score = (
            0.4 * total_return
            + 0.3 * sharpe
            + 0.2 * win_rate
            + 0.1 * (1 + max_dd)  # max_dd is negative, so 1+max_dd penalizes deep drawdowns
        )

        return OptimizationResult(
            params=params,
            total_trades=total_trades,
            winning_trades=winning,
            win_rate=win_rate,
            total_return=total_return,
            max_drawdown=max_dd,
            sharpe_ratio=sharpe,
            score=score,
        )
