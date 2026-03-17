"""
Ichimoku Cloud Strategy
=======================
Trend-following strategy based on the Ichimoku Kinko Hyo cloud system.

Uses Tenkan-sen/Kijun-sen crossovers confirmed by cloud position.
"""

from __future__ import annotations

from typing import Any

from .base import Strategy, StrategySignal, StrategyMeta


class IchimokuStrategy(Strategy):
    """Ichimoku Cloud trend-following strategy.

    Parameters:
        tenkan_period: Tenkan-sen (conversion line) period.
        kijun_period: Kijun-sen (base line) period.
        senkou_b_period: Senkou Span B period.
        initial_capital: Starting capital for backtesting.
    """

    def __init__(
        self,
        tenkan_period: int = 9,
        kijun_period: int = 26,
        senkou_b_period: int = 52,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.tenkan_period = tenkan_period
        self.kijun_period = kijun_period
        self.senkou_b_period = senkou_b_period

    @classmethod
    def meta(cls) -> StrategyMeta:
        return StrategyMeta(
            name="Ichimoku Cloud",
            slug="ichimoku",
            category="universal",
            description=(
                "Japanese Ichimoku Kinko Hyo (one-glance equilibrium) strategy. "
                "Uses Tenkan-sen/Kijun-sen crossovers, confirmed by price position "
                "relative to the Kumo (cloud), for trend-following signals."
            ),
            parameters={
                "tenkan_period": "Conversion line period (default: 9)",
                "kijun_period": "Base line period (default: 26)",
                "senkou_b_period": "Senkou Span B period (default: 52)",
            },
            usage_example=(
                'from src.strategies.library.ichimoku import IchimokuStrategy\n'
                'strategy = IchimokuStrategy(tenkan_period=9, kijun_period=26)\n'
                'signals = strategy.generate_signals(ohlcv_data)'
            ),
        )

    @staticmethod
    def _midpoint(data: list[dict[str, Any]], end: int, period: int) -> float | None:
        """Calculate (highest high + lowest low) / 2 over period ending at `end`."""
        if end < period - 1:
            return None
        window = data[end - period + 1 : end + 1]
        highs = [bar["high"] for bar in window]
        lows = [bar["low"] for bar in window]
        return (max(highs) + min(lows)) / 2

    def generate_signals(self, data: list[dict[str, Any]]) -> list[StrategySignal]:
        """Generate signals using Ichimoku cloud components."""
        signals: list[StrategySignal] = []
        min_needed = self.senkou_b_period

        for i in range(len(data)):
            if i < min_needed:
                signals.append(StrategySignal(action="hold", confidence=0.0))
                continue

            tenkan = self._midpoint(data, i, self.tenkan_period)
            kijun = self._midpoint(data, i, self.kijun_period)
            senkou_a = (tenkan + kijun) / 2 if tenkan is not None and kijun is not None else None
            senkou_b = self._midpoint(data, i, self.senkou_b_period)

            if any(v is None for v in (tenkan, kijun, senkou_a, senkou_b)):
                signals.append(StrategySignal(action="hold", confidence=0.0))
                continue

            close = data[i]["close"]
            cloud_top = max(senkou_a, senkou_b)  # type: ignore[arg-type]
            cloud_bottom = min(senkou_a, senkou_b)  # type: ignore[arg-type]

            # Bullish: Tenkan > Kijun AND price above cloud
            if tenkan > kijun and close > cloud_top:  # type: ignore[operator]
                distance = (close - cloud_top) / cloud_top if cloud_top > 0 else 0
                confidence = min(1.0, 0.5 + distance * 5)
                signals.append(StrategySignal(
                    action="buy", confidence=confidence,
                    price=close,
                    reason=f"Bullish: TK cross above cloud (tenkan={tenkan:.2f}, kijun={kijun:.2f})",
                ))
            # Bearish: Tenkan < Kijun AND price below cloud
            elif tenkan < kijun and close < cloud_bottom:  # type: ignore[operator]
                distance = (cloud_bottom - close) / cloud_bottom if cloud_bottom > 0 else 0
                confidence = min(1.0, 0.5 + distance * 5)
                signals.append(StrategySignal(
                    action="sell", confidence=confidence,
                    price=close,
                    reason=f"Bearish: TK cross below cloud (tenkan={tenkan:.2f}, kijun={kijun:.2f})",
                ))
            else:
                signals.append(StrategySignal(action="hold", confidence=0.0))

        return signals
