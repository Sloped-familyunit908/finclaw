"""
VWAP Strategy
=============
Volume-Weighted Average Price reversion strategy.

Buys when price is significantly below VWAP (oversold).
Sells when price is significantly above VWAP (overbought).
"""

from __future__ import annotations

import math
from typing import Any

from .base import Strategy, StrategySignal, StrategyMeta


class VWAPStrategy(Strategy):
    """Volume-Weighted Average Price mean reversion strategy.

    Parameters:
        lookback: Number of bars for VWAP calculation.
        std_dev: Standard deviation threshold for signals.
        initial_capital: Starting capital for backtesting.
    """

    def __init__(self, lookback: int = 20, std_dev: float = 2.0, **kwargs: Any):
        super().__init__(**kwargs)
        self.lookback = lookback
        self.std_dev = std_dev

    @classmethod
    def meta(cls) -> StrategyMeta:
        return StrategyMeta(
            name="VWAP Reversion",
            slug="vwap",
            category="universal",
            description=(
                "Mean reversion strategy using Volume-Weighted Average Price. "
                "Buys when price falls below VWAP by a configurable number of "
                "standard deviations, sells when it rises above."
            ),
            parameters={
                "lookback": "Number of bars for VWAP calculation (default: 20)",
                "std_dev": "Standard deviation threshold for entry (default: 2.0)",
            },
            usage_example=(
                'from src.strategies.library.vwap import VWAPStrategy\n'
                'strategy = VWAPStrategy(lookback=20, std_dev=2.0)\n'
                'signals = strategy.generate_signals(ohlcv_data)'
            ),
        )

    def generate_signals(self, data: list[dict[str, Any]]) -> list[StrategySignal]:
        """Generate signals based on price deviation from VWAP."""
        signals: list[StrategySignal] = []

        for i in range(len(data)):
            if i < self.lookback:
                signals.append(StrategySignal(action="hold", confidence=0.0))
                continue

            window = data[i - self.lookback + 1 : i + 1]

            # Calculate VWAP
            cum_tp_vol = 0.0
            cum_vol = 0.0
            prices_in_window: list[float] = []
            for bar in window:
                typical_price = (bar["high"] + bar["low"] + bar["close"]) / 3
                vol = bar.get("volume", 1)
                cum_tp_vol += typical_price * vol
                cum_vol += vol
                prices_in_window.append(typical_price)

            vwap = cum_tp_vol / cum_vol if cum_vol > 0 else data[i]["close"]

            # Standard deviation of typical prices
            mean_tp = sum(prices_in_window) / len(prices_in_window)
            variance = sum((p - mean_tp) ** 2 for p in prices_in_window) / len(prices_in_window)
            std = math.sqrt(variance) if variance > 0 else 1.0

            current_price = data[i]["close"]
            z_score = (current_price - vwap) / std if std > 0 else 0.0

            if z_score < -self.std_dev:
                confidence = min(1.0, abs(z_score) / (self.std_dev * 2))
                signals.append(StrategySignal(
                    action="buy", confidence=confidence,
                    price=current_price,
                    reason=f"Price below VWAP by {abs(z_score):.1f} std devs",
                ))
            elif z_score > self.std_dev:
                confidence = min(1.0, abs(z_score) / (self.std_dev * 2))
                signals.append(StrategySignal(
                    action="sell", confidence=confidence,
                    price=current_price,
                    reason=f"Price above VWAP by {z_score:.1f} std devs",
                ))
            else:
                signals.append(StrategySignal(action="hold", confidence=0.0))

        return signals
