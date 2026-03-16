"""
Walk-Forward Optimization v2 — Anchored & Rolling with Parameter Grid Search.

Optimizes strategy parameters on in-sample data, validates on out-of-sample,
and tracks parameter stability and overfitting ratio across windows.
"""

import math
import itertools
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol

import numpy as np
import pandas as pd


class Strategy(Protocol):
    """Protocol that strategy classes must implement."""
    def run(self, data: pd.DataFrame, **params) -> pd.Series:
        """Return a series of daily returns."""
        ...


@dataclass
class WindowResult:
    """Result for a single walk-forward window."""
    window_id: int
    train_start: Any
    train_end: Any
    test_start: Any
    test_end: Any
    best_params: dict
    is_sharpe: float
    is_cagr: float
    oos_sharpe: float
    oos_cagr: float
    oos_returns: list[float] = field(default_factory=list)


@dataclass
class WalkForwardResult:
    """Aggregated walk-forward optimization result."""
    windows: list[WindowResult]
    oos_sharpe: float
    oos_cagr: float
    param_stability: float  # 0=stable, 1=chaotic
    overfitting_ratio: float  # IS mean / OOS mean (>2 = likely overfit)
    best_params_per_window: list[dict] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            "=== Walk-Forward Optimization Report ===",
            f"Windows: {len(self.windows)}",
            f"OOS Sharpe: {self.oos_sharpe:.3f}",
            f"OOS CAGR: {self.oos_cagr:.2%}",
            f"Param Stability: {self.param_stability:.3f} ({'stable' if self.param_stability < 0.3 else 'unstable'})",
            f"Overfitting Ratio: {self.overfitting_ratio:.2f} ({'OK' if self.overfitting_ratio < 2.0 else 'WARNING'})",
        ]
        return "\n".join(lines)


def _sharpe(returns: np.ndarray) -> float:
    """Annualized Sharpe ratio from daily returns."""
    if len(returns) < 2 or np.std(returns) == 0:
        return 0.0
    return float(np.mean(returns) / np.std(returns) * math.sqrt(252))


def _cagr(returns: np.ndarray) -> float:
    """CAGR from daily returns."""
    if len(returns) == 0:
        return 0.0
    cum = np.prod(1 + returns)
    years = len(returns) / 252
    if years <= 0 or cum <= 0:
        return 0.0
    return float(cum ** (1 / years) - 1)


def _metric_fn(returns: np.ndarray, metric: str) -> float:
    if metric == 'sharpe':
        return _sharpe(returns)
    elif metric == 'cagr':
        return _cagr(returns)
    elif metric == 'sortino':
        down = returns[returns < 0]
        if len(down) < 2 or np.std(down) == 0:
            return 0.0
        return float(np.mean(returns) / np.std(down) * math.sqrt(252))
    return _sharpe(returns)


class WalkForwardOptimizer:
    """
    Walk-forward optimizer with anchored and rolling modes.

    Anchored: training window always starts from the beginning.
    Rolling: training window slides forward.
    """

    def __init__(self, train_pct: float = 0.7, anchored: bool = False,
                 n_windows: int = 5, min_train_bars: int = 60):
        if not 0.1 <= train_pct <= 0.95:
            raise ValueError("train_pct must be between 0.1 and 0.95")
        if n_windows < 2:
            raise ValueError("n_windows must be >= 2")
        self.train_pct = train_pct
        self.anchored = anchored
        self.n_windows = n_windows
        self.min_train_bars = min_train_bars

    def _generate_windows(self, n_bars: int) -> list[tuple[int, int, int, int]]:
        """Generate (train_start, train_end, test_start, test_end) tuples."""
        windows = []
        if self.anchored:
            # Anchored: train always starts at 0, expanding window
            test_size = max(1, int(n_bars * (1 - self.train_pct) / self.n_windows))
            for i in range(self.n_windows):
                test_start = int(n_bars * self.train_pct) + i * test_size
                test_end = min(test_start + test_size, n_bars)
                if test_start >= n_bars:
                    break
                windows.append((0, test_start, test_start, test_end))
        else:
            # Rolling: fixed-size train window slides
            total_per_window = n_bars // self.n_windows
            train_size = max(self.min_train_bars, int(total_per_window * self.train_pct))
            test_size = max(1, total_per_window - train_size)
            step = train_size + test_size

            for i in range(self.n_windows):
                ts = i * test_size
                te = ts + train_size
                os_start = te
                os_end = min(os_start + test_size, n_bars)
                if os_start >= n_bars or te > n_bars:
                    break
                windows.append((ts, te, os_start, os_end))

        return windows

    def optimize(self, strategy_fn: Callable[..., np.ndarray],
                 param_grid: dict, data: pd.DataFrame,
                 metric: str = 'sharpe') -> WalkForwardResult:
        """
        Run walk-forward optimization.

        Args:
            strategy_fn: Callable(data, **params) -> np.ndarray of daily returns
            param_grid: Dict of param_name -> list of values to search
            data: DataFrame with price data
            metric: 'sharpe', 'cagr', or 'sortino'

        Returns:
            WalkForwardResult with OOS performance and stability metrics.
        """
        n_bars = len(data)
        windows = self._generate_windows(n_bars)

        if len(windows) < 2:
            raise ValueError(f"Not enough data ({n_bars} bars) for {self.n_windows} windows")

        # Generate all parameter combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combos = list(itertools.product(*param_values))

        results: list[WindowResult] = []

        for wid, (ts, te, os_s, os_e) in enumerate(windows):
            train_data = data.iloc[ts:te]
            test_data = data.iloc[os_s:os_e]

            if len(train_data) < self.min_train_bars or len(test_data) == 0:
                continue

            # Grid search on training data
            best_score = -np.inf
            best_params = {}
            best_is_returns = np.array([])

            for combo in combos:
                params = dict(zip(param_names, combo))
                try:
                    returns = np.asarray(strategy_fn(train_data, **params), dtype=float)
                    score = _metric_fn(returns, metric)
                    if score > best_score:
                        best_score = score
                        best_params = params
                        best_is_returns = returns
                except Exception:
                    continue

            if not best_params:
                continue

            # Apply best params to OOS
            try:
                oos_returns = np.asarray(strategy_fn(test_data, **best_params), dtype=float)
            except Exception:
                continue

            wr = WindowResult(
                window_id=wid,
                train_start=ts, train_end=te,
                test_start=os_s, test_end=os_e,
                best_params=best_params,
                is_sharpe=_sharpe(best_is_returns),
                is_cagr=_cagr(best_is_returns),
                oos_sharpe=_sharpe(oos_returns),
                oos_cagr=_cagr(oos_returns),
                oos_returns=oos_returns.tolist(),
            )
            results.append(wr)

        if not results:
            return WalkForwardResult(
                windows=[], oos_sharpe=0, oos_cagr=0,
                param_stability=1.0, overfitting_ratio=float('inf'),
            )

        # Aggregate OOS metrics
        all_oos = np.concatenate([np.array(w.oos_returns) for w in results])
        oos_sharpe = _sharpe(all_oos)
        oos_cagr = _cagr(all_oos)

        # Overfitting ratio: mean IS sharpe / mean OOS sharpe
        mean_is = np.mean([w.is_sharpe for w in results])
        mean_oos = np.mean([w.oos_sharpe for w in results])
        overfit_ratio = abs(mean_is) / max(abs(mean_oos), 0.001)

        # Parameter stability: normalized std of params across windows
        param_stability = self._calc_param_stability(results, param_grid)

        return WalkForwardResult(
            windows=results,
            oos_sharpe=oos_sharpe,
            oos_cagr=oos_cagr,
            param_stability=param_stability,
            overfitting_ratio=overfit_ratio,
            best_params_per_window=[w.best_params for w in results],
        )

    @staticmethod
    def _calc_param_stability(results: list[WindowResult], param_grid: dict) -> float:
        """Calculate how much parameters change across windows (0=stable, 1=chaotic)."""
        if len(results) < 2:
            return 0.0

        stabilities = []
        for pname, pvals in param_grid.items():
            chosen = []
            for w in results:
                v = w.best_params.get(pname)
                if v is not None:
                    try:
                        chosen.append(float(v))
                    except (TypeError, ValueError):
                        continue
            if len(chosen) < 2:
                continue
            val_range = max(float(v) for v in pvals) - min(float(v) for v in pvals)
            if val_range > 0:
                stabilities.append(np.std(chosen) / val_range)

        return float(np.mean(stabilities)) if stabilities else 0.0
