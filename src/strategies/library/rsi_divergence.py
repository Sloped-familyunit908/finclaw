"""
RSI Divergence Strategy
=======================
Detects bullish/bearish divergences between price and RSI.

Bullish divergence: price makes lower low, RSI makes higher low → buy.
Bearish divergence: price makes higher high, RSI makes lower high → sell.
"""

from __future__ import annotations

from typing import Any

from .base import Strategy, StrategySignal, StrategyMeta, rsi as compute_rsi


class RSIDivergenceStrategy(Strategy):
    """RSI/price divergence detection strategy.

    Parameters:
        rsi_period: RSI calculation period.
        lookback: Bars to look back for divergence detection.
        initial_capital: Starting capital for backtesting.
    """

    def __init__(self, rsi_period: int = 14, lookback: int = 10, **kwargs: Any):
        super().__init__(**kwargs)
        self.rsi_period = rsi_period
        self.lookback = lookback

    @classmethod
    def meta(cls) -> StrategyMeta:
        return StrategyMeta(
            name="RSI Divergence",
            slug="rsi-divergence",
            category="universal",
            description=(
                "Detects bullish and bearish divergences between price and RSI. "
                "Bullish divergence (price lower low + RSI higher low) generates buy signals. "
                "Bearish divergence (price higher high + RSI lower high) generates sell signals."
            ),
            parameters={
                "rsi_period": "RSI calculation period (default: 14)",
                "lookback": "Bars to look back for divergence (default: 10)",
            },
            usage_example=(
                'from src.strategies.library.rsi_divergence import RSIDivergenceStrategy\n'
                'strategy = RSIDivergenceStrategy(rsi_period=14, lookback=10)\n'
                'signals = strategy.generate_signals(ohlcv_data)'
            ),
        )

    def generate_signals(self, data: list[dict[str, Any]]) -> list[StrategySignal]:
        """Generate signals based on RSI divergence."""
        signals: list[StrategySignal] = []
        closes = [bar["close"] for bar in data]
        min_needed = self.rsi_period + self.lookback + 1

        for i in range(len(data)):
            if i < min_needed:
                signals.append(StrategySignal(action="hold", confidence=0.0))
                continue

            # Compute RSI at current and lookback point
            rsi_now = compute_rsi(closes[: i + 1], self.rsi_period)
            rsi_prev = compute_rsi(closes[: i - self.lookback + 1], self.rsi_period)

            if rsi_now is None or rsi_prev is None:
                signals.append(StrategySignal(action="hold", confidence=0.0))
                continue

            price_now = closes[i]
            price_prev = closes[i - self.lookback]

            # Bullish divergence: price lower low, RSI higher low
            if price_now < price_prev and rsi_now > rsi_prev:
                confidence = min(1.0, (rsi_now - rsi_prev) / 20.0)
                signals.append(StrategySignal(
                    action="buy", confidence=max(0.1, confidence),
                    price=price_now,
                    reason=f"Bullish divergence: price ↓ RSI ↑ (RSI={rsi_now:.1f})",
                ))
            # Bearish divergence: price higher high, RSI lower high
            elif price_now > price_prev and rsi_now < rsi_prev:
                confidence = min(1.0, (rsi_prev - rsi_now) / 20.0)
                signals.append(StrategySignal(
                    action="sell", confidence=max(0.1, confidence),
                    price=price_now,
                    reason=f"Bearish divergence: price ↑ RSI ↓ (RSI={rsi_now:.1f})",
                ))
            else:
                signals.append(StrategySignal(action="hold", confidence=0.0))

        return signals
