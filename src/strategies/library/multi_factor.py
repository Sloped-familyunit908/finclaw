"""
Multi-Factor Model
==================
Combines value, momentum, and quality factors for stock selection.

Parameters:
    value_weight: Weight for value factor (default: 0.3).
    momentum_weight: Weight for momentum factor (default: 0.4).
    quality_weight: Weight for quality factor (default: 0.3).
    buy_threshold: Combined score to buy (default: 0.5).
    sell_threshold: Combined score to sell (default: -0.3).
    sma_period: SMA for value calc (default: 200).
    momentum_lookback: Momentum lookback bars (default: 252).

Usage:
    strategy = MultiFactorStrategy(value_weight=0.3, momentum_weight=0.4)
    signals = strategy.generate_signals(data_with_fundamentals)

Data format:
    Each bar should include 'close' and optionally 'pe_ratio', 'roe', 'debt_equity'.
"""

from __future__ import annotations
import math
from typing import Any
from .base import Strategy, StrategySignal, StrategyMeta


class MultiFactorStrategy(Strategy):
    """Multi-factor model: value + momentum + quality."""

    def __init__(
        self,
        value_weight: float = 0.3,
        momentum_weight: float = 0.4,
        quality_weight: float = 0.3,
        buy_threshold: float = 0.5,
        sell_threshold: float = -0.3,
        sma_period: int = 200,
        momentum_lookback: int = 252,
        initial_capital: float = 10_000,
    ):
        super().__init__(initial_capital=initial_capital)
        self.value_weight = value_weight
        self.momentum_weight = momentum_weight
        self.quality_weight = quality_weight
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.sma_period = sma_period
        self.momentum_lookback = momentum_lookback

    @classmethod
    def meta(cls) -> StrategyMeta:
        return StrategyMeta(
            name="Multi-Factor Model",
            slug="multi-factor",
            category="universal",
            description="Combines value, momentum, and quality factors for stock scoring.",
            parameters={
                "value_weight": "Weight for value factor (default: 0.3)",
                "momentum_weight": "Weight for momentum factor (default: 0.4)",
                "quality_weight": "Weight for quality factor (default: 0.3)",
                "buy_threshold": "Score threshold to buy (default: 0.5)",
                "sell_threshold": "Score threshold to sell (default: -0.3)",
            },
            usage_example="finclaw strategy backtest multi-factor --symbol AAPL --start 2024-01-01",
        )

    def _value_score(self, closes: list[float]) -> float:
        """Value = discount to long-term SMA. Clamped to [-1, 1]."""
        if len(closes) < self.sma_period:
            return 0.0
        avg = sum(closes[-self.sma_period:]) / self.sma_period
        if avg <= 0:
            return 0.0
        discount = (avg - closes[-1]) / avg
        return max(-1.0, min(1.0, discount * 2))

    def _momentum_score(self, closes: list[float]) -> float:
        """Momentum = return over lookback. Clamped to [-1, 1]."""
        if len(closes) < self.momentum_lookback + 1:
            return 0.0
        past = closes[-(self.momentum_lookback + 1)]
        if past <= 0:
            return 0.0
        ret = (closes[-1] - past) / past
        return max(-1.0, min(1.0, ret))

    def _quality_score(self, bar: dict[str, Any]) -> float:
        """Quality from fundamentals. Uses ROE and debt/equity if available."""
        score = 0.0
        n = 0
        roe = bar.get("roe")
        if roe is not None:
            score += max(-1.0, min(1.0, (roe - 0.10) / 0.15))
            n += 1
        de = bar.get("debt_equity")
        if de is not None:
            score += max(-1.0, min(1.0, (1.0 - de) / 1.0))
            n += 1
        return score / n if n > 0 else 0.0

    def generate_signals(self, data: list[dict[str, Any]]) -> list[StrategySignal]:
        signals: list[StrategySignal] = []
        closes = [bar["close"] for bar in data]

        for i in range(len(data)):
            price = data[i]["close"]
            if i < self.sma_period or i < self.momentum_lookback + 1:
                signals.append(StrategySignal("hold", 0.0, price=price, reason="warming up"))
                continue

            v = self._value_score(closes[: i + 1])
            m = self._momentum_score(closes[: i + 1])
            q = self._quality_score(data[i])
            combined = v * self.value_weight + m * self.momentum_weight + q * self.quality_weight

            if combined >= self.buy_threshold:
                signals.append(StrategySignal(
                    "buy", min(combined, 1.0), price=price,
                    reason=f"score={combined:.2f} (V={v:.2f} M={m:.2f} Q={q:.2f})",
                    metadata={"value": v, "momentum": m, "quality": q, "combined": combined},
                ))
            elif combined <= self.sell_threshold:
                signals.append(StrategySignal(
                    "sell", min(abs(combined), 1.0), price=price,
                    reason=f"score={combined:.2f} (V={v:.2f} M={m:.2f} Q={q:.2f})",
                    metadata={"value": v, "momentum": m, "quality": q, "combined": combined},
                ))
            else:
                signals.append(StrategySignal(
                    "hold", 0.0, price=price,
                    reason=f"score={combined:.2f}, neutral",
                    metadata={"value": v, "momentum": m, "quality": q, "combined": combined},
                ))

        return signals
