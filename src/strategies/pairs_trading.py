"""
Pairs Trading Strategy
Cointegration-based pair selection with z-score entry/exit.
"""

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class PairSignal:
    asset_a: str
    asset_b: str
    spread: float
    z_score: float
    hedge_ratio: float
    signal: str  # "long_a_short_b", "short_a_long_b", "close", "hold"
    confidence: float
    reason: str


class PairsTradingStrategy:
    """
    Statistical arbitrage using spread z-score.
    
    Enter when z-score > entry_z (or < -entry_z).
    Exit when z-score crosses zero or hits stop.
    """

    def __init__(
        self,
        lookback: int = 60,
        entry_z: float = 2.0,
        exit_z: float = 0.5,
        stop_z: float = 3.5,
    ):
        self.lookback = lookback
        self.entry_z = entry_z
        self.exit_z = exit_z
        self.stop_z = stop_z

    def compute_hedge_ratio(self, prices_a: list[float], prices_b: list[float]) -> float:
        """OLS hedge ratio: A = beta * B + alpha."""
        n = min(len(prices_a), len(prices_b), self.lookback)
        if n < 10:
            return 1.0
        a = prices_a[-n:]
        b = prices_b[-n:]
        mean_a = sum(a) / n
        mean_b = sum(b) / n
        cov = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n)) / n
        var_b = sum((b[i] - mean_b) ** 2 for i in range(n)) / n
        return cov / max(var_b, 1e-10)

    def compute_spread(
        self, prices_a: list[float], prices_b: list[float], hedge_ratio: float
    ) -> list[float]:
        n = min(len(prices_a), len(prices_b))
        return [prices_a[-n + i] - hedge_ratio * prices_b[-n + i] for i in range(n)]

    def cointegration_score(self, spread: list[float]) -> float:
        """
        Simplified ADF-like stationarity test.
        Returns a score 0-1 where higher = more likely cointegrated.
        Based on mean-reversion speed.
        """
        if len(spread) < 20:
            return 0.0
        # Compute autocorrelation at lag 1
        mean_s = sum(spread) / len(spread)
        demeaned = [s - mean_s for s in spread]
        var_s = sum(d**2 for d in demeaned) / len(demeaned)
        if var_s < 1e-10:
            return 1.0
        cov_1 = sum(demeaned[i] * demeaned[i-1] for i in range(1, len(demeaned))) / len(demeaned)
        rho = cov_1 / var_s
        # Strong mean reversion: rho close to 0 or negative
        return max(0, min(1, 1 - rho))

    def generate_signal(
        self,
        asset_a: str,
        asset_b: str,
        prices_a: list[float],
        prices_b: list[float],
    ) -> PairSignal:
        n = min(len(prices_a), len(prices_b))
        if n < self.lookback:
            return PairSignal(asset_a, asset_b, 0, 0, 1.0, "hold", 0, "insufficient data")

        hr = self.compute_hedge_ratio(prices_a, prices_b)
        spread = self.compute_spread(prices_a, prices_b, hr)

        window = spread[-self.lookback:]
        mean_s = sum(window) / len(window)
        std_s = math.sqrt(sum((s - mean_s)**2 for s in window) / len(window))
        if std_s < 1e-10:
            return PairSignal(asset_a, asset_b, spread[-1], 0, hr, "hold", 0, "no variance")

        z = (spread[-1] - mean_s) / std_s
        coint = self.cointegration_score(spread)

        if abs(z) > self.stop_z:
            return PairSignal(asset_a, asset_b, spread[-1], z, hr, "close", 0.8,
                              f"z={z:.2f} hit stop")

        if z > self.entry_z and coint > 0.3:
            conf = min(0.9, 0.4 + coint * 0.3 + (z - self.entry_z) * 0.1)
            return PairSignal(asset_a, asset_b, spread[-1], z, hr,
                              "short_a_long_b", conf, f"z={z:.2f} spread too high")

        if z < -self.entry_z and coint > 0.3:
            conf = min(0.9, 0.4 + coint * 0.3 + (-z - self.entry_z) * 0.1)
            return PairSignal(asset_a, asset_b, spread[-1], z, hr,
                              "long_a_short_b", conf, f"z={z:.2f} spread too low")

        if abs(z) < self.exit_z:
            return PairSignal(asset_a, asset_b, spread[-1], z, hr,
                              "close", 0.5, f"z={z:.2f} mean reverted")

        return PairSignal(asset_a, asset_b, spread[-1], z, hr, "hold", 0.3, f"z={z:.2f}")
