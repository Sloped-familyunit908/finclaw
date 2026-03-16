"""
Value at Risk (VaR) Calculator
Historical and Parametric VaR/CVaR.
"""

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class VaRResult:
    confidence: float      # e.g. 0.95
    var: float             # VaR as a negative return (e.g. -0.025)
    cvar: float            # CVaR / Expected Shortfall
    var_dollar: float      # VaR in dollar terms
    cvar_dollar: float
    method: str            # "historical" or "parametric"


class VaRCalculator:
    """Historical and parametric Value at Risk."""

    def __init__(self, confidence: float = 0.95):
        self.confidence = confidence

    def historical(self, daily_returns: list[float], portfolio_value: float = 10000) -> VaRResult:
        """
        Historical VaR: sort returns, take the (1-confidence) percentile.
        """
        if len(daily_returns) < 10:
            return VaRResult(self.confidence, 0, 0, 0, 0, "historical")

        sorted_rets = sorted(daily_returns)
        n = len(sorted_rets)
        idx = max(int(n * (1 - self.confidence)), 0)
        idx = min(idx, n - 1)

        var = sorted_rets[idx]
        # CVaR = average of returns worse than VaR
        tail = sorted_rets[:idx + 1]
        cvar = sum(tail) / max(len(tail), 1)

        return VaRResult(
            confidence=self.confidence,
            var=var,
            cvar=cvar,
            var_dollar=var * portfolio_value,
            cvar_dollar=cvar * portfolio_value,
            method="historical",
        )

    def parametric(self, daily_returns: list[float], portfolio_value: float = 10000) -> VaRResult:
        """
        Parametric (Gaussian) VaR: assume normal distribution.
        VaR = mean - z * std
        """
        if len(daily_returns) < 10:
            return VaRResult(self.confidence, 0, 0, 0, 0, "parametric")

        mean = sum(daily_returns) / len(daily_returns)
        std = math.sqrt(
            sum((r - mean)**2 for r in daily_returns) / (len(daily_returns) - 1)
        )

        # z-scores for common confidence levels
        z_map = {0.90: 1.282, 0.95: 1.645, 0.99: 2.326}
        z = z_map.get(self.confidence, 1.645)

        var = mean - z * std
        # Parametric CVaR for normal distribution
        # E[X | X < VaR] = mean - std * phi(z) / (1 - confidence)
        phi_z = math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)
        cvar = mean - std * phi_z / (1 - self.confidence)

        return VaRResult(
            confidence=self.confidence,
            var=var,
            cvar=cvar,
            var_dollar=var * portfolio_value,
            cvar_dollar=cvar * portfolio_value,
            method="parametric",
        )
