"""Yield curve construction, interpolation, and analytics."""

from __future__ import annotations

import math


class YieldCurve:
    """A yield curve built from tenor-rate pairs with interpolation.

    Parameters
    ----------
    tenors : list of floats – maturities in years (e.g. [0.25, 0.5, 1, 2, 5, 10, 30])
    rates : list of floats – annualized yields (e.g. [0.045, 0.046, ...])
    """

    def __init__(self, tenors: list[float], rates: list[float]) -> None:
        if len(tenors) != len(rates):
            raise ValueError("tenors and rates must have the same length")
        if len(tenors) < 2:
            raise ValueError("Need at least 2 data points")

        # Sort by tenor
        paired = sorted(zip(tenors, rates))
        self.tenors = [t for t, _ in paired]
        self.rates = [r for _, r in paired]

    def interpolate(self, tenor: float) -> float:
        """Linear interpolation (flat extrapolation at boundaries)."""
        if tenor <= self.tenors[0]:
            return self.rates[0]
        if tenor >= self.tenors[-1]:
            return self.rates[-1]

        for i in range(len(self.tenors) - 1):
            if self.tenors[i] <= tenor <= self.tenors[i + 1]:
                t0, t1 = self.tenors[i], self.tenors[i + 1]
                r0, r1 = self.rates[i], self.rates[i + 1]
                frac = (tenor - t0) / (t1 - t0)
                return r0 + frac * (r1 - r0)

        return self.rates[-1]  # fallback

    def forward_rate(self, t1: float, t2: float) -> float:
        """Implied forward rate between t1 and t2.

        Uses: (1+r2)^t2 = (1+r1)^t1 * (1+f)^(t2-t1)
        """
        if t2 <= t1:
            raise ValueError("t2 must be greater than t1")

        r1 = self.interpolate(t1)
        r2 = self.interpolate(t2)

        # Continuous compounding: f = (r2*t2 - r1*t1) / (t2 - t1)
        return (r2 * t2 - r1 * t1) / (t2 - t1)

    def discount_factor(self, tenor: float) -> float:
        """Discount factor at a given tenor using continuous compounding."""
        rate = self.interpolate(tenor)
        return math.exp(-rate * tenor)

    def is_inverted(self) -> bool:
        """Check if the yield curve is inverted (short rates > long rates)."""
        if len(self.tenors) < 2:
            return False
        short_rate = self.rates[0]
        long_rate = self.rates[-1]
        return short_rate > long_rate
