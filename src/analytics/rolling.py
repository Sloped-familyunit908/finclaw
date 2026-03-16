"""
Rolling Returns Analysis
Compute rolling Sharpe, returns, and volatility over sliding windows.
"""

import math
from dataclasses import dataclass


@dataclass
class RollingPoint:
    index: int
    rolling_return: float
    rolling_sharpe: float
    rolling_volatility: float


class RollingAnalysis:
    """Sliding window analysis of returns."""

    def __init__(self, window: int = 63):  # ~3 months
        self.window = window

    def compute(self, daily_returns: list[float], risk_free: float = 0.05) -> list[RollingPoint]:
        results = []
        for i in range(self.window, len(daily_returns)):
            w = daily_returns[i - self.window:i]
            cum_ret = 1.0
            for r in w:
                cum_ret *= (1 + r)
            cum_ret -= 1

            mean = sum(w) / len(w)
            if len(w) > 1:
                std = math.sqrt(sum((r - mean)**2 for r in w) / (len(w) - 1))
            else:
                std = 0
            ann_std = std * math.sqrt(252)
            ann_mean = mean * 252
            sharpe = (ann_mean - risk_free) / max(ann_std, 0.001)

            results.append(RollingPoint(
                index=i,
                rolling_return=cum_ret,
                rolling_sharpe=sharpe,
                rolling_volatility=ann_std,
            ))
        return results
