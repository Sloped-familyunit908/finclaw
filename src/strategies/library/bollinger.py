"""
Bollinger Bands Mean Reversion Strategy
========================================
Trades mean reversion using Bollinger Bands with RSI and %B confirmations.

Unlike the simpler ``MeanReversionBBStrategy``, this strategy uses:
- %B (percent B) for precise band position measurement
- Band squeeze detection for volatility breakouts
- Trend filter via middle band slope

Parameters:
    period: Bollinger Bands period (default: 20).
    num_std: Number of standard deviations (default: 2.0).
    buy_pct_b: Buy when %B drops below this (default: 0.0 = lower band).
    sell_pct_b: Sell when %B rises above this (default: 1.0 = upper band).
    squeeze_threshold: Bandwidth threshold for squeeze detection (default: 0.04).

Usage:
    strategy = BollingerStrategy(period=20, num_std=2.0)
    signals = strategy.generate_signals(ohlcv_data)
"""

from __future__ import annotations
import math
from typing import Any
from .base import Strategy, StrategySignal, StrategyMeta, rsi as calc_rsi


class BollingerStrategy(Strategy):
    """Bollinger Bands mean reversion with squeeze detection."""

    def __init__(
        self,
        period: int = 20,
        num_std: float = 2.0,
        buy_pct_b: float = 0.0,
        sell_pct_b: float = 1.0,
        squeeze_threshold: float = 0.04,
        rsi_period: int = 14,
        initial_capital: float = 10_000,
    ):
        super().__init__(initial_capital=initial_capital)
        if period < 2:
            raise ValueError("period must be >= 2")
        if num_std <= 0:
            raise ValueError("num_std must be > 0")
        self.period = period
        self.num_std = num_std
        self.buy_pct_b = buy_pct_b
        self.sell_pct_b = sell_pct_b
        self.squeeze_threshold = squeeze_threshold
        self.rsi_period = rsi_period

    @classmethod
    def meta(cls) -> StrategyMeta:
        return StrategyMeta(
            name="Bollinger Bands",
            slug="bollinger",
            category="universal",
            description="Mean reversion using Bollinger Bands with %B, RSI confirmation, "
                        "and squeeze detection for breakout awareness.",
            parameters={
                "period": "BB period (default: 20)",
                "num_std": "Standard deviations (default: 2.0)",
                "buy_pct_b": "Buy below this %B level (default: 0.0)",
                "sell_pct_b": "Sell above this %B level (default: 1.0)",
                "squeeze_threshold": "Bandwidth squeeze threshold (default: 0.04)",
                "rsi_period": "RSI confirmation period (default: 14)",
            },
            usage_example="finclaw strategy backtest bollinger --symbol SPY --start 2024-01-01",
        )

    def _compute_bb(self, prices: list[float]) -> tuple[float, float, float, float, float] | None:
        """Compute (upper, middle, lower, pct_b, bandwidth) from recent prices.

        Returns None if insufficient data.
        """
        if len(prices) < self.period:
            return None

        window = prices[-self.period:]
        mid = sum(window) / self.period
        variance = sum((p - mid) ** 2 for p in window) / self.period
        std = math.sqrt(variance)

        upper = mid + self.num_std * std
        lower = mid - self.num_std * std

        band_range = upper - lower
        pct_b = (prices[-1] - lower) / band_range if band_range > 0 else 0.5
        bandwidth = band_range / mid if mid > 0 else 0.0

        return upper, mid, lower, pct_b, bandwidth

    def generate_signals(self, data: list[dict[str, Any]]) -> list[StrategySignal]:
        signals: list[StrategySignal] = []
        closes = [bar["close"] for bar in data]
        min_bars = max(self.period, self.rsi_period + 1)

        prev_bandwidth: float | None = None

        for i in range(len(data)):
            price = data[i]["close"]

            if i < min_bars:
                signals.append(StrategySignal("hold", 0.0, price=price, reason="warming up"))
                continue

            bb = self._compute_bb(closes[: i + 1])
            rsi_val = calc_rsi(closes[: i + 1], self.rsi_period)

            if bb is None:
                signals.append(StrategySignal("hold", 0.0, price=price, reason="insufficient data"))
                continue

            upper, mid, lower, pct_b, bandwidth = bb

            # Detect squeeze (low volatility → potential breakout)
            in_squeeze = bandwidth < self.squeeze_threshold

            # Middle band slope (trend direction over last 5 bars)
            if i >= self.period + 5:
                prev_bb = self._compute_bb(closes[: i - 4])
                if prev_bb is not None:
                    mid_slope = (mid - prev_bb[1]) / max(abs(prev_bb[1]), 0.01)
                else:
                    mid_slope = 0
            else:
                mid_slope = 0

            metadata = {
                "pct_b": pct_b,
                "bandwidth": bandwidth,
                "in_squeeze": in_squeeze,
                "mid_slope": mid_slope,
                "rsi": rsi_val,
                "upper": upper,
                "lower": lower,
            }

            # Buy: price at or below lower band, RSI confirms oversold
            if pct_b <= self.buy_pct_b and not in_squeeze:
                rsi_ok = rsi_val is not None and rsi_val < 40
                if rsi_ok or rsi_val is None:
                    confidence = min(max(0, -pct_b) + 0.5, 1.0)
                    if rsi_val is not None and rsi_val < 25:
                        confidence = min(confidence + 0.2, 1.0)
                    signals.append(StrategySignal(
                        "buy", confidence, price=price,
                        reason=f"at lower BB (%B={pct_b:.2f}, RSI={rsi_val:.1f})" if rsi_val else f"at lower BB (%B={pct_b:.2f})",
                        metadata=metadata,
                    ))
                else:
                    signals.append(StrategySignal("hold", 0.0, price=price,
                                                  reason=f"%B={pct_b:.2f} but RSI={rsi_val:.1f} not oversold",
                                                  metadata=metadata))
            # Sell: price at or above upper band, RSI confirms overbought
            elif pct_b >= self.sell_pct_b and not in_squeeze:
                rsi_ok = rsi_val is not None and rsi_val > 60
                if rsi_ok or rsi_val is None:
                    confidence = min(max(0, pct_b - 1.0) + 0.5, 1.0)
                    if rsi_val is not None and rsi_val > 75:
                        confidence = min(confidence + 0.2, 1.0)
                    signals.append(StrategySignal(
                        "sell", confidence, price=price,
                        reason=f"at upper BB (%B={pct_b:.2f}, RSI={rsi_val:.1f})" if rsi_val else f"at upper BB (%B={pct_b:.2f})",
                        metadata=metadata,
                    ))
                else:
                    signals.append(StrategySignal("hold", 0.0, price=price,
                                                  reason=f"%B={pct_b:.2f} but RSI={rsi_val:.1f} not overbought",
                                                  metadata=metadata))
            else:
                reason = f"%B={pct_b:.2f}, BW={bandwidth:.4f}"
                if in_squeeze:
                    reason += " [SQUEEZE]"
                signals.append(StrategySignal("hold", 0.0, price=price, reason=reason, metadata=metadata))

            prev_bandwidth = bandwidth

        return signals
