"""
Value + Momentum Combo Strategy
Fama-French inspired multi-factor: combine value and momentum signals.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ValueMomentumSignal:
    signal: str
    confidence: float
    value_score: float     # -1 to 1
    momentum_score: float  # -1 to 1
    combined_score: float
    reason: str


class ValueMomentumStrategy:
    """
    Multi-factor strategy combining value and momentum.
    
    Value: price relative to moving averages (discount = value)
    Momentum: 12-1 month return
    Combined: weighted average of both factors.
    """

    def __init__(
        self,
        value_weight: float = 0.4,
        momentum_weight: float = 0.6,
        sma_period: int = 200,
        momentum_lookback: int = 252,
        momentum_skip: int = 21,
        buy_threshold: float = 0.3,
        sell_threshold: float = -0.3,
    ):
        self.value_weight = value_weight
        self.momentum_weight = momentum_weight
        self.sma_period = sma_period
        self.momentum_lookback = momentum_lookback
        self.momentum_skip = momentum_skip
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

    def generate_signal(self, prices: list[float]) -> ValueMomentumSignal:
        needed = max(self.sma_period, self.momentum_lookback + self.momentum_skip) + 1
        if len(prices) < needed:
            return ValueMomentumSignal("hold", 0, 0, 0, 0, "insufficient data")

        value_score = self._value_score(prices)
        mom_score = self._momentum_score(prices)
        combined = self.value_weight * value_score + self.momentum_weight * mom_score

        if combined > self.buy_threshold:
            conf = min(0.9, 0.4 + abs(combined) * 0.5)
            parts = []
            if value_score > 0:
                parts.append(f"value={value_score:.2f}")
            if mom_score > 0:
                parts.append(f"momentum={mom_score:.2f}")
            return ValueMomentumSignal("buy", conf, value_score, mom_score, combined,
                                       f"combined={combined:.2f} ({', '.join(parts)})")

        if combined < self.sell_threshold:
            conf = min(0.9, 0.4 + abs(combined) * 0.5)
            return ValueMomentumSignal("sell", conf, value_score, mom_score, combined,
                                       f"combined={combined:.2f}")

        return ValueMomentumSignal("hold", 0.3, value_score, mom_score, combined,
                                    f"combined={combined:.2f} neutral")

    def _value_score(self, prices: list[float]) -> float:
        """
        Value score based on discount to SMA.
        Larger discount = higher value score.
        """
        sma = sum(prices[-self.sma_period:]) / self.sma_period
        price = prices[-1]
        discount = (sma - price) / sma  # positive = undervalued
        # Normalize to [-1, 1]
        return max(-1, min(1, discount * 5))

    def _momentum_score(self, prices: list[float]) -> float:
        """
        12-1 month momentum score.
        """
        p_now = prices[-self.momentum_skip] if len(prices) > self.momentum_skip else prices[-1]
        p_past = prices[-(self.momentum_lookback + self.momentum_skip)]
        mom = (p_now / p_past) - 1
        # Normalize: 20% return -> score ~0.5
        return max(-1, min(1, mom * 2.5))

    def rank_assets(self, asset_prices: dict[str, list[float]]) -> list[dict]:
        """Rank multiple assets by combined score."""
        results = []
        for symbol, prices in asset_prices.items():
            sig = self.generate_signal(prices)
            results.append({
                "symbol": symbol,
                "combined_score": sig.combined_score,
                "value_score": sig.value_score,
                "momentum_score": sig.momentum_score,
                "signal": sig.signal,
            })
        results.sort(key=lambda x: x["combined_score"], reverse=True)
        return results
