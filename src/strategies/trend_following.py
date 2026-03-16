"""
Trend Following Strategy
Dual moving average crossover with ADX filter.
Only trades when ADX > threshold (strong trend).
"""

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class TrendSignal:
    signal: str  # buy, sell, hold
    confidence: float
    fast_ma: float
    slow_ma: float
    adx: Optional[float]
    trend_strength: str  # strong, moderate, weak, none
    reason: str


class TrendFollowingStrategy:
    """Dual MA crossover + ADX trend filter."""

    def __init__(
        self,
        fast_period: int = 20,
        slow_period: int = 50,
        adx_period: int = 14,
        adx_threshold: float = 25.0,
    ):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold

    def generate_signal(
        self,
        prices: list[float],
        highs: Optional[list[float]] = None,
        lows: Optional[list[float]] = None,
    ) -> TrendSignal:
        if len(prices) < self.slow_period + 2:
            return TrendSignal("hold", 0, 0, 0, None, "none", "insufficient data")

        fast_ma = sum(prices[-self.fast_period:]) / self.fast_period
        slow_ma = sum(prices[-self.slow_period:]) / self.slow_period
        prev_fast = sum(prices[-self.fast_period-1:-1]) / self.fast_period
        prev_slow = sum(prices[-self.slow_period-1:-1]) / self.slow_period

        # ADX calculation
        adx = None
        if highs and lows and len(highs) >= self.adx_period + 2:
            adx = self._adx(highs, lows, prices)

        # Trend strength
        if adx is not None:
            if adx > 40:
                strength = "strong"
            elif adx > self.adx_threshold:
                strength = "moderate"
            elif adx > 15:
                strength = "weak"
            else:
                strength = "none"
        else:
            # Fallback: use MA separation
            sep = abs(fast_ma - slow_ma) / slow_ma if slow_ma else 0
            strength = "moderate" if sep > 0.02 else "weak" if sep > 0.005 else "none"

        # Crossover detection
        cross_up = prev_fast <= prev_slow and fast_ma > slow_ma
        cross_down = prev_fast >= prev_slow and fast_ma < slow_ma
        above = fast_ma > slow_ma

        # ADX filter
        trend_ok = adx is None or adx > self.adx_threshold

        if cross_up and trend_ok:
            conf = 0.7 if strength in ("strong", "moderate") else 0.45
            return TrendSignal("buy", conf, fast_ma, slow_ma, adx, strength,
                               "golden cross" + (f" ADX={adx:.1f}" if adx else ""))

        if cross_down and trend_ok:
            conf = 0.7 if strength in ("strong", "moderate") else 0.45
            return TrendSignal("sell", conf, fast_ma, slow_ma, adx, strength,
                               "death cross" + (f" ADX={adx:.1f}" if adx else ""))

        if above and trend_ok and strength in ("strong", "moderate"):
            return TrendSignal("buy", 0.4, fast_ma, slow_ma, adx, strength, "uptrend holds")

        if not above and trend_ok and strength in ("strong", "moderate"):
            return TrendSignal("sell", 0.4, fast_ma, slow_ma, adx, strength, "downtrend holds")

        return TrendSignal("hold", 0.2, fast_ma, slow_ma, adx, strength, "no clear trend")

    def _adx(self, highs: list[float], lows: list[float], closes: list[float]) -> Optional[float]:
        """Compute ADX."""
        n = len(highs)
        if n < self.adx_period + 2:
            return None

        tr_list = []
        plus_dm = []
        minus_dm = []

        for i in range(1, n):
            h, l, pc = highs[i], lows[i], closes[i-1]
            tr_list.append(max(h - l, abs(h - pc), abs(l - pc)))
            up = highs[i] - highs[i-1]
            down = lows[i-1] - lows[i]
            plus_dm.append(up if up > down and up > 0 else 0)
            minus_dm.append(down if down > up and down > 0 else 0)

        p = self.adx_period
        if len(tr_list) < p:
            return None

        atr = sum(tr_list[:p]) / p
        plus_di_sum = sum(plus_dm[:p]) / p
        minus_di_sum = sum(minus_dm[:p]) / p

        dx_list = []
        for i in range(p, len(tr_list)):
            atr = (atr * (p - 1) + tr_list[i]) / p
            plus_di_sum = (plus_di_sum * (p - 1) + plus_dm[i]) / p
            minus_di_sum = (minus_di_sum * (p - 1) + minus_dm[i]) / p

            plus_di = 100 * plus_di_sum / max(atr, 1e-10)
            minus_di = 100 * minus_di_sum / max(atr, 1e-10)
            di_sum = plus_di + minus_di
            dx = 100 * abs(plus_di - minus_di) / max(di_sum, 1e-10) if di_sum > 0 else 0
            dx_list.append(dx)

        if len(dx_list) < p:
            return sum(dx_list) / max(len(dx_list), 1)

        adx = sum(dx_list[:p]) / p
        for i in range(p, len(dx_list)):
            adx = (adx * (p - 1) + dx_list[i]) / p
        return adx
