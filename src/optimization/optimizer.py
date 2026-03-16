"""
Strategy Optimizer
Grid search / random search over strategy parameters with walk-forward validation.
"""

import itertools
import math
import random
from dataclasses import dataclass, field
from typing import Any, Optional, Type


@dataclass
class OptimizationResult:
    """Result of a single parameter combination evaluation."""
    params: dict[str, Any]
    sharpe_ratio: float
    total_return: float
    max_drawdown: float
    win_rate: float
    num_trades: int
    metric_value: float  # the optimized metric


@dataclass
class WalkForwardResult:
    """Walk-forward validation result."""
    in_sample: OptimizationResult
    out_of_sample: OptimizationResult
    robustness_ratio: float  # OOS metric / IS metric


@dataclass
class OptimizationReport:
    """Full optimization report."""
    best_params: dict[str, Any]
    best_metric: float
    all_results: list[OptimizationResult]
    walk_forward: Optional[list[WalkForwardResult]] = None
    method: str = "grid"
    total_combinations: int = 0


class StrategyOptimizer:
    """
    Optimize strategy parameters via grid/random search.
    
    Usage:
        optimizer = StrategyOptimizer(strategy_cls=MeanReversionStrategy)
        report = optimizer.optimize(
            param_grid={'rsi_period': [10, 14, 20], 'rsi_oversold': [25, 30, 35]},
            data=prices,
            metric='sharpe_ratio',
            method='grid',
        )
    """

    SUPPORTED_METRICS = ("sharpe_ratio", "total_return", "max_drawdown", "win_rate")

    def __init__(self, strategy_cls: Type):
        self.strategy_cls = strategy_cls

    def optimize(
        self,
        param_grid: dict[str, list[Any]],
        data: list[float],
        metric: str = "sharpe_ratio",
        method: str = "grid",
        max_iter: int = 100,
        walk_forward: bool = False,
        wf_train_ratio: float = 0.7,
        wf_windows: int = 3,
        seed: int = 42,
    ) -> OptimizationReport:
        """Run optimization."""
        if metric not in self.SUPPORTED_METRICS:
            raise ValueError(f"Unsupported metric: {metric}. Use one of {self.SUPPORTED_METRICS}")
        if len(data) < 30:
            raise ValueError("Need at least 30 data points")

        combos = self._generate_combinations(param_grid, method, max_iter, seed)
        results = []
        for params in combos:
            result = self._evaluate(params, data, metric)
            results.append(result)

        results.sort(key=lambda r: r.metric_value, reverse=(metric != "max_drawdown"))
        best = results[0]

        wf_results = None
        if walk_forward and len(data) >= 60:
            wf_results = self._walk_forward_validate(
                param_grid, data, metric, method, max_iter,
                wf_train_ratio, wf_windows, seed,
            )

        return OptimizationReport(
            best_params=best.params,
            best_metric=best.metric_value,
            all_results=results,
            walk_forward=wf_results,
            method=method,
            total_combinations=len(combos),
        )

    def _generate_combinations(
        self, param_grid: dict, method: str, max_iter: int, seed: int,
    ) -> list[dict]:
        keys = list(param_grid.keys())
        values = list(param_grid.values())

        if method == "grid":
            return [dict(zip(keys, combo)) for combo in itertools.product(*values)]
        elif method == "random":
            rng = random.Random(seed)
            combos = []
            for _ in range(max_iter):
                combo = {k: rng.choice(v) for k, v in param_grid.items()}
                combos.append(combo)
            return combos
        else:
            raise ValueError(f"Unsupported method: {method}. Use 'grid' or 'random'")

    def _evaluate(
        self, params: dict, data: list[float], metric: str,
    ) -> OptimizationResult:
        """Evaluate a strategy with given params on data."""
        strategy = self.strategy_cls(**params)
        trades = self._simulate_trades(strategy, data)

        total_return = self._calc_return(trades, data)
        sharpe = self._calc_sharpe(trades, data)
        mdd = self._calc_max_drawdown(data, trades)
        win_rate = self._calc_win_rate(trades)

        metric_map = {
            "sharpe_ratio": sharpe,
            "total_return": total_return,
            "max_drawdown": mdd,
            "win_rate": win_rate,
        }

        return OptimizationResult(
            params=params,
            sharpe_ratio=sharpe,
            total_return=total_return,
            max_drawdown=mdd,
            win_rate=win_rate,
            num_trades=len(trades),
            metric_value=metric_map[metric],
        )

    def _simulate_trades(self, strategy, data: list[float]) -> list[dict]:
        """Simple trade simulation: generate signals and track trades."""
        trades = []
        position = None  # (entry_price, entry_idx)
        window = 30  # minimum window before generating signals

        for i in range(window, len(data)):
            prices_slice = data[:i + 1]
            signal = self._get_signal(strategy, prices_slice)

            if position is None and signal == "buy":
                position = (data[i], i)
            elif position is not None and signal == "sell":
                entry_price, entry_idx = position
                exit_price = data[i]
                pnl_pct = (exit_price / entry_price) - 1
                trades.append({
                    "entry": entry_price, "exit": exit_price,
                    "entry_idx": entry_idx, "exit_idx": i,
                    "pnl_pct": pnl_pct,
                })
                position = None

        return trades

    def _get_signal(self, strategy, prices: list[float]) -> str:
        """Extract signal string from various strategy types."""
        if hasattr(strategy, "generate_signal"):
            result = strategy.generate_signal(prices)
            return result.signal if hasattr(result, "signal") else "hold"
        elif hasattr(strategy, "score_single"):
            result = strategy.score_single(prices)
            return result.signal if hasattr(result, "signal") else "hold"
        elif hasattr(strategy, "signal"):
            val = strategy.signal(prices)
            if isinstance(val, (int, float)):
                if val > 0.3:
                    return "buy"
                elif val < -0.3:
                    return "sell"
                return "hold"
            return str(val)
        return "hold"

    def _calc_return(self, trades: list[dict], data: list[float]) -> float:
        if not trades:
            return 0.0
        compounded = 1.0
        for t in trades:
            compounded *= (1 + t["pnl_pct"])
        return compounded - 1

    def _calc_sharpe(self, trades: list[dict], data: list[float], rf: float = 0.02) -> float:
        if len(trades) < 2:
            return 0.0
        returns = [t["pnl_pct"] for t in trades]
        mean_r = sum(returns) / len(returns)
        std_r = math.sqrt(sum((r - mean_r) ** 2 for r in returns) / len(returns))
        if std_r == 0:
            return 0.0
        # Annualize assuming ~20 trades/year
        annual_factor = math.sqrt(max(1, min(252, len(trades))))
        return (mean_r - rf / 252) * annual_factor / std_r

    def _calc_max_drawdown(self, data: list[float], trades: list[dict]) -> float:
        if not data:
            return 0.0
        peak = data[0]
        max_dd = 0.0
        for p in data:
            if p > peak:
                peak = p
            dd = (peak - p) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        return max_dd

    def _calc_win_rate(self, trades: list[dict]) -> float:
        if not trades:
            return 0.0
        wins = sum(1 for t in trades if t["pnl_pct"] > 0)
        return wins / len(trades)

    def _walk_forward_validate(
        self, param_grid, data, metric, method, max_iter,
        train_ratio, num_windows, seed,
    ) -> list[WalkForwardResult]:
        """Walk-forward: train on in-sample, test on out-of-sample, slide."""
        n = len(data)
        window_size = n // num_windows
        results = []

        for w in range(num_windows):
            start = w * (window_size // 2)
            end = min(start + window_size, n)
            if end - start < 40:
                continue

            split = start + int((end - start) * train_ratio)
            train_data = data[start:split]
            test_data = data[split:end]

            if len(train_data) < 30 or len(test_data) < 10:
                continue

            # Optimize on train
            combos = self._generate_combinations(param_grid, method, max_iter, seed)
            train_results = [self._evaluate(p, train_data, metric) for p in combos]
            train_results.sort(
                key=lambda r: r.metric_value,
                reverse=(metric != "max_drawdown"),
            )
            best_train = train_results[0]

            # Test on OOS
            oos_result = self._evaluate(best_train.params, test_data, metric)

            is_metric = best_train.metric_value if best_train.metric_value != 0 else 1e-9
            robustness = oos_result.metric_value / is_metric

            results.append(WalkForwardResult(
                in_sample=best_train,
                out_of_sample=oos_result,
                robustness_ratio=robustness,
            ))

        return results
