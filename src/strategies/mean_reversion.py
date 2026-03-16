"""
Mean Reversion Strategy
RSI oversold/overbought with Bollinger Bands confirmation.
Buy when RSI < 30 AND price touches lower BB; sell when RSI > 70 or upper BB.
"""

from dataclasses import dataclass
from typing import Optional
import math


@dataclass
class MeanReversionSignal:
    signal: str  # buy, sell, hold
    confidence: float
    rsi: Optional[float]
    bb_position: Optional[float]  # 0 = lower band, 1 = upper band
    reason: str


class MeanReversionStrategy:
    """RSI + Bollinger Bands mean reversion."""

    def __init__(
        self,
        rsi_period: int = 14,
        rsi_oversold: float = 30,
        rsi_overbought: float = 70,
        bb_period: int = 20,
        bb_std: float = 2.0,
    ):
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.bb_period = bb_period
        self.bb_std = bb_std

    def generate_signal(self, prices: list[float]) -> MeanReversionSignal:
        if len(prices) < max(self.rsi_period + 1, self.bb_period):
            return MeanReversionSignal("hold", 0, None, None, "insufficient data")

        rsi = self._rsi(prices)
        bb_upper, bb_mid, bb_lower = self._bollinger(prices)
        price = prices[-1]

        # BB position: 0 = at lower, 1 = at upper
        bb_range = bb_upper - bb_lower if bb_upper != bb_lower else 1
        bb_pos = (price - bb_lower) / bb_range

        if rsi is not None and rsi < self.rsi_oversold and bb_pos < 0.1:
            conf = min(0.9, 0.5 + (self.rsi_oversold - rsi) / 100 + (0.1 - bb_pos))
            return MeanReversionSignal("buy", conf, rsi, bb_pos,
                                       f"RSI={rsi:.1f} oversold + near lower BB")

        if rsi is not None and rsi > self.rsi_overbought and bb_pos > 0.9:
            conf = min(0.9, 0.5 + (rsi - self.rsi_overbought) / 100 + (bb_pos - 0.9))
            return MeanReversionSignal("sell", conf, rsi, bb_pos,
                                       f"RSI={rsi:.1f} overbought + near upper BB")

        # Moderate signals
        if rsi is not None and rsi < 35 and bb_pos < 0.2:
            return MeanReversionSignal("buy", 0.4, rsi, bb_pos, "mild oversold")
        if rsi is not None and rsi > 65 and bb_pos > 0.8:
            return MeanReversionSignal("sell", 0.4, rsi, bb_pos, "mild overbought")

        return MeanReversionSignal("hold", 0.3, rsi, bb_pos, "no signal")

    def _rsi(self, prices: list[float]) -> Optional[float]:
        if len(prices) < self.rsi_period + 1:
            return None
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [max(d, 0) for d in deltas]
        losses = [max(-d, 0) for d in deltas]
        avg_gain = sum(gains[:self.rsi_period]) / self.rsi_period
        avg_loss = sum(losses[:self.rsi_period]) / self.rsi_period
        for i in range(self.rsi_period, len(gains)):
            avg_gain = (avg_gain * (self.rsi_period - 1) + gains[i]) / self.rsi_period
            avg_loss = (avg_loss * (self.rsi_period - 1) + losses[i]) / self.rsi_period
        if avg_loss == 0:
            return 100.0
        return 100 - 100 / (1 + avg_gain / avg_loss)

    def _bollinger(self, prices: list[float]):
        period = min(self.bb_period, len(prices))
        window = prices[-period:]
        mid = sum(window) / period
        std = math.sqrt(sum((p - mid)**2 for p in window) / period)
        return mid + self.bb_std * std, mid, mid - self.bb_std * std
