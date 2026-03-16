"""
Portfolio-Level Risk Management
Max drawdown limits, correlation-based allocation.
"""

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AllocationResult:
    weights: dict[str, float]       # symbol -> weight (0-1)
    total_risk: float               # portfolio volatility
    max_drawdown_budget: float
    reason: str


class PortfolioRiskManager:
    """
    Portfolio-level risk constraints.
    - Max drawdown circuit breaker
    - Correlation-aware allocation (equal risk contribution)
    """

    def __init__(
        self,
        max_drawdown_limit: float = 0.20,
        max_single_position: float = 0.30,
        max_correlated_exposure: float = 0.50,
    ):
        self.max_drawdown_limit = max_drawdown_limit
        self.max_single_position = max_single_position
        self.max_correlated_exposure = max_correlated_exposure

    def check_drawdown_circuit_breaker(
        self, equity_curve: list[float]
    ) -> tuple[bool, float]:
        """
        Returns (should_halt, current_drawdown).
        Halts trading if drawdown exceeds limit.
        """
        if not equity_curve:
            return False, 0.0
        peak = equity_curve[0]
        max_dd = 0
        for eq in equity_curve:
            peak = max(peak, eq)
            dd = (eq - peak) / peak if peak > 0 else 0
            max_dd = min(max_dd, dd)
        current_dd = (equity_curve[-1] - peak) / peak if peak > 0 else 0
        should_halt = current_dd < -self.max_drawdown_limit
        return should_halt, current_dd

    def equal_weight_allocation(self, symbols: list[str]) -> AllocationResult:
        """Simple equal-weight allocation with position cap."""
        n = len(symbols)
        if n == 0:
            return AllocationResult({}, 0, self.max_drawdown_limit, "no symbols")
        w = min(1.0 / n, self.max_single_position)
        weights = {s: w for s in symbols}
        return AllocationResult(weights, 0, self.max_drawdown_limit, f"equal weight 1/{n}")

    def inverse_volatility_allocation(
        self, symbol_vols: dict[str, float]
    ) -> AllocationResult:
        """
        Allocate inversely proportional to volatility.
        Lower vol assets get bigger weights.
        """
        if not symbol_vols:
            return AllocationResult({}, 0, self.max_drawdown_limit, "no data")

        inv_vols = {s: 1.0 / max(v, 0.001) for s, v in symbol_vols.items()}
        total_inv = sum(inv_vols.values())
        weights = {}
        for s, iv in inv_vols.items():
            w = iv / total_inv
            weights[s] = min(w, self.max_single_position)

        # Renormalize
        total_w = sum(weights.values())
        if total_w > 0:
            weights = {s: w / total_w for s, w in weights.items()}

        return AllocationResult(
            weights, 0, self.max_drawdown_limit,
            "inverse volatility"
        )

    def correlation_check(
        self,
        returns_a: list[float],
        returns_b: list[float],
    ) -> float:
        """Compute correlation between two return series."""
        n = min(len(returns_a), len(returns_b))
        if n < 3:
            return 0.0
        a = returns_a[-n:]
        b = returns_b[-n:]
        ma = sum(a) / n
        mb = sum(b) / n
        cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n)) / (n - 1)
        sa = math.sqrt(sum((x - ma)**2 for x in a) / (n - 1))
        sb = math.sqrt(sum((x - mb)**2 for x in b) / (n - 1))
        if sa * sb == 0:
            return 0.0
        return cov / (sa * sb)
