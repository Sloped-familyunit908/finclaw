"""
Trend Following — Dual MA + ADX Filter
=======================================
Buy when fast MA crosses above slow MA and ADX confirms a strong trend.

Parameters:
    fast_period: Fast moving average period (default: 20).
    slow_period: Slow moving average period (default: 50).
    adx_period: ADX calculation period (default: 14).
    adx_threshold: Minimum ADX to confirm trend (default: 25).

Usage:
    strategy = TrendFollowingStrategy(fast_period=10, slow_period=30)
    signals = strategy.generate_signals(ohlcv_data)
    result = strategy.backtest(ohlcv_data)
"""

from __future__ import annotations
from typing import Any
from .base import Strategy, StrategySignal, StrategyMeta, sma, adx as calc_adx


class TrendFollowingStrategy(Strategy):
    """Dual Moving Average crossover with ADX trend filter."""

    def __init__(
        self,
        fast_period: int = 20,
        slow_period: int = 50,
        adx_period: int = 14,
        adx_threshold: float = 25.0,
        initial_capital: float = 10_000,
    ):
        super().__init__(initial_capital=initial_capital)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold

    @classmethod
    def meta(cls) -> StrategyMeta:
        return StrategyMeta(
            name="Trend Following",
            slug="trend-following",
            category="universal",
            description="Dual MA crossover with ADX trend filter. Only trades in strong trends.",
            parameters={
                "fast_period": "Fast MA period (default: 20)",
                "slow_period": "Slow MA period (default: 50)",
                "adx_period": "ADX period (default: 14)",
                "adx_threshold": "Min ADX to trade (default: 25)",
            },
            usage_example="finclaw strategy backtest trend-following --symbol AAPL --start 2024-01-01",
        )

    def generate_signals(self, data: list[dict[str, Any]]) -> list[StrategySignal]:
        signals: list[StrategySignal] = []
        closes = [bar["close"] for bar in data]
        highs = [bar.get("high", bar["close"]) for bar in data]
        lows = [bar.get("low", bar["close"]) for bar in data]

        for i in range(len(data)):
            if i < self.slow_period + 1:
                signals.append(StrategySignal("hold", 0.0, price=data[i]["close"], reason="warming up"))
                continue

            fast = sma(closes[: i + 1], self.fast_period)
            slow = sma(closes[: i + 1], self.slow_period)
            prev_fast = sma(closes[:i], self.fast_period)
            prev_slow = sma(closes[:i], self.slow_period)

            adx_val = calc_adx(highs[: i + 1], lows[: i + 1], closes[: i + 1], self.adx_period)

            if fast is None or slow is None or prev_fast is None or prev_slow is None:
                signals.append(StrategySignal("hold", 0.0, price=data[i]["close"], reason="insufficient data"))
                continue

            strong_trend = adx_val is not None and adx_val >= self.adx_threshold

            # Golden cross
            if prev_fast <= prev_slow and fast > slow and strong_trend:
                signals.append(StrategySignal(
                    "buy", min((adx_val or 0) / 50, 1.0), price=data[i]["close"],
                    reason=f"golden cross, ADX={adx_val:.1f}" if adx_val else "golden cross",
                    metadata={"fast_ma": fast, "slow_ma": slow, "adx": adx_val},
                ))
            # Death cross
            elif prev_fast >= prev_slow and fast < slow:
                signals.append(StrategySignal(
                    "sell", 0.7, price=data[i]["close"],
                    reason=f"death cross, ADX={adx_val:.1f}" if adx_val else "death cross",
                    metadata={"fast_ma": fast, "slow_ma": slow, "adx": adx_val},
                ))
            else:
                signals.append(StrategySignal("hold", 0.0, price=data[i]["close"], reason="no crossover"))

        return signals
