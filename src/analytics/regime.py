"""
Regime-Conditional Performance Analysis
Classify market regimes (bull/bear/sideways) and measure strategy performance in each.
"""

import math
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class Regime(Enum):
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"


@dataclass
class RegimePerformance:
    regime: Regime
    n_bars: int
    total_return: float
    sharpe: float
    max_drawdown: float
    win_rate: float
    n_trades: int


class RegimeAnalyzer:
    """
    Classify regimes using SMA trend and volatility.
    Then slice backtest performance by regime.
    """

    def __init__(self, sma_period: int = 50, vol_lookback: int = 20, vol_threshold: float = 0.02):
        self.sma_period = sma_period
        self.vol_lookback = vol_lookback
        self.vol_threshold = vol_threshold

    def classify_regimes(self, prices: list[float]) -> list[Regime]:
        """Classify each bar into a regime."""
        regimes = []
        for i in range(len(prices)):
            if i < self.sma_period:
                regimes.append(Regime.SIDEWAYS)
                continue
            sma = sum(prices[i - self.sma_period:i]) / self.sma_period
            price = prices[i]
            # Volatility
            if i >= self.vol_lookback:
                rets = [(prices[j] / prices[j-1]) - 1 for j in range(i - self.vol_lookback + 1, i + 1)]
                vol = math.sqrt(sum(r**2 for r in rets) / len(rets)) if rets else 0
            else:
                vol = 0

            if price > sma * 1.02:
                regimes.append(Regime.BULL)
            elif price < sma * 0.98:
                regimes.append(Regime.BEAR)
            else:
                regimes.append(Regime.SIDEWAYS)
        return regimes

    def analyze_by_regime(
        self,
        prices: list[float],
        daily_returns: list[float],
        trades: list,
        warmup: int = 20,
    ) -> list[RegimePerformance]:
        """Compute performance metrics for each regime."""
        regimes = self.classify_regimes(prices)
        # Align daily_returns to regimes (offset by warmup)
        regime_returns: dict[Regime, list[float]] = {r: [] for r in Regime}
        for i, ret in enumerate(daily_returns):
            bar_idx = i + warmup + 1
            if bar_idx < len(regimes):
                regime_returns[regimes[bar_idx]].append(ret)

        results = []
        for regime, rets in regime_returns.items():
            n = len(rets)
            if n == 0:
                results.append(RegimePerformance(regime, 0, 0, 0, 0, 0, 0))
                continue

            cum = 1.0
            peak = 1.0
            max_dd = 0
            for r in rets:
                cum *= (1 + r)
                peak = max(peak, cum)
                dd = (cum - peak) / peak if peak > 0 else 0
                max_dd = min(max_dd, dd)

            total_ret = cum - 1
            mean = sum(rets) / n * 252
            std = math.sqrt(sum((r - sum(rets)/n)**2 for r in rets) / max(n-1, 1)) * math.sqrt(252)
            sharpe = (mean - 0.05) / max(std, 0.001)

            results.append(RegimePerformance(
                regime=regime, n_bars=n, total_return=total_ret,
                sharpe=sharpe, max_drawdown=max_dd, win_rate=0, n_trades=0,
            ))
        return results
