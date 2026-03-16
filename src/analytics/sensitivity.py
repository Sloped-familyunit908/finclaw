"""
Strategy Parameter Sensitivity Analysis.

Tests how sensitive a strategy's performance is to parameter changes,
identifies optimal values and dangerous cliff edges.
"""

import math
from dataclasses import dataclass, field
from typing import Callable, Any, Optional

import numpy as np
import pandas as pd


@dataclass
class SensitivityResult:
    """Result of sensitivity analysis for one parameter."""
    param: str
    values: list
    results: list[dict] = field(default_factory=list)  # {value, sharpe, cagr, max_dd}
    optimal: Any = None
    optimal_sharpe: float = 0.0
    sensitivity: str = 'low'  # 'low', 'medium', 'high'
    sensitivity_score: float = 0.0  # Normalized std of performance
    cliff_edges: list[dict] = field(default_factory=list)  # {from_value, to_value, drop}
    monotonic: Optional[str] = None  # 'increasing', 'decreasing', None

    def summary(self) -> str:
        lines = [
            f"=== Sensitivity Analysis: {self.param} ===",
            f"Values tested: {len(self.values)}",
            f"Optimal: {self.optimal} (Sharpe={self.optimal_sharpe:.3f})",
            f"Sensitivity: {self.sensitivity} (score={self.sensitivity_score:.3f})",
        ]
        if self.cliff_edges:
            lines.append(f"Cliff edges: {len(self.cliff_edges)}")
            for ce in self.cliff_edges:
                lines.append(
                    f"  {ce['from_value']} -> {ce['to_value']}: "
                    f"Sharpe drop {ce['drop']:.3f}"
                )
        if self.monotonic:
            lines.append(f"Trend: {self.monotonic}")
        return "\n".join(lines)


def _sharpe(returns: np.ndarray) -> float:
    if len(returns) < 2 or np.std(returns) == 0:
        return 0.0
    return float(np.mean(returns) / np.std(returns) * math.sqrt(252))


def _cagr(returns: np.ndarray) -> float:
    if len(returns) == 0:
        return 0.0
    cum = np.prod(1 + returns)
    years = len(returns) / 252
    if years <= 0 or cum <= 0:
        return 0.0
    return float(cum ** (1 / years) - 1)


def _max_drawdown(returns: np.ndarray) -> float:
    if len(returns) == 0:
        return 0.0
    cum = np.cumprod(1 + returns)
    peak = np.maximum.accumulate(cum)
    dd = (cum - peak) / peak
    return float(np.min(dd))


class SensitivityAnalyzer:
    """Analyze strategy sensitivity to parameter changes."""

    def __init__(self, cliff_threshold: float = 0.5):
        """
        Args:
            cliff_threshold: Sharpe drop threshold to flag as cliff edge
        """
        self.cliff_threshold = cliff_threshold

    def analyze(self, strategy_fn: Callable[..., np.ndarray],
                data: pd.DataFrame, param_name: str,
                values: list, **fixed_params) -> SensitivityResult:
        """
        Test strategy with different values of one parameter.

        Args:
            strategy_fn: Callable(data, **params) -> np.ndarray of daily returns
            data: Price data DataFrame
            param_name: Name of the parameter to vary
            values: List of values to test
            **fixed_params: Other parameters held constant

        Returns:
            SensitivityResult with performance across values and cliff detection.
        """
        results = []
        sharpes = []

        for val in values:
            params = {**fixed_params, param_name: val}
            try:
                returns = np.asarray(strategy_fn(data, **params), dtype=float)
                s = _sharpe(returns)
                c = _cagr(returns)
                dd = _max_drawdown(returns)
                results.append({
                    'value': val,
                    'sharpe': s,
                    'cagr': c,
                    'max_dd': dd,
                })
                sharpes.append(s)
            except Exception:
                results.append({
                    'value': val,
                    'sharpe': 0.0,
                    'cagr': 0.0,
                    'max_dd': 0.0,
                })
                sharpes.append(0.0)

        if not results:
            return SensitivityResult(param=param_name, values=values)

        # Find optimal
        best_idx = int(np.argmax(sharpes))
        optimal = values[best_idx]
        optimal_sharpe = sharpes[best_idx]

        # Sensitivity score: coefficient of variation of Sharpe
        sharpe_arr = np.array(sharpes)
        if optimal_sharpe != 0:
            sensitivity_score = float(np.std(sharpe_arr) / max(abs(np.mean(sharpe_arr)), 0.001))
        else:
            sensitivity_score = 0.0

        if sensitivity_score > 1.0:
            sensitivity = 'high'
        elif sensitivity_score > 0.3:
            sensitivity = 'medium'
        else:
            sensitivity = 'low'

        # Detect cliff edges
        cliff_edges = []
        for i in range(1, len(sharpes)):
            drop = sharpes[i - 1] - sharpes[i]
            if abs(drop) > self.cliff_threshold:
                cliff_edges.append({
                    'from_value': values[i - 1],
                    'to_value': values[i],
                    'drop': float(drop),
                })

        # Check monotonicity
        monotonic = None
        if len(sharpes) >= 3:
            diffs = np.diff(sharpes)
            if np.all(diffs >= -0.01):
                monotonic = 'increasing'
            elif np.all(diffs <= 0.01):
                monotonic = 'decreasing'

        return SensitivityResult(
            param=param_name,
            values=values,
            results=results,
            optimal=optimal,
            optimal_sharpe=optimal_sharpe,
            sensitivity=sensitivity,
            sensitivity_score=sensitivity_score,
            cliff_edges=cliff_edges,
            monotonic=monotonic,
        )

    def analyze_multi(self, strategy_fn: Callable[..., np.ndarray],
                      data: pd.DataFrame,
                      param_grid: dict[str, list],
                      **fixed_params) -> dict[str, SensitivityResult]:
        """
        Analyze sensitivity for multiple parameters independently.

        Args:
            strategy_fn: Strategy function
            data: Price data
            param_grid: Dict of param_name -> list of values
            **fixed_params: Fixed parameters

        Returns:
            Dict mapping param names to SensitivityResult.
        """
        results = {}
        for param_name, values in param_grid.items():
            results[param_name] = self.analyze(
                strategy_fn, data, param_name, values, **fixed_params
            )
        return results
