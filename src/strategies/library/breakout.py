"""
Breakout Strategy — Donchian Channel + Volume
==============================================
Buy on upper channel breakout with volume confirmation.

Parameters:
    channel_period: Donchian channel lookback (default: 20).
    volume_multiplier: Min volume vs SMA to confirm (default: 1.5).
    volume_period: Volume SMA period (default: 20).
    exit_period: Exit channel period, shorter (default: 10).

Usage:
    strategy = BreakoutStrategy(channel_period=20, volume_multiplier=1.5)
    signals = strategy.generate_signals(ohlcv_data)
"""

from __future__ import annotations
from typing import Any
from .base import Strategy, StrategySignal, StrategyMeta, donchian_channel


class BreakoutStrategy(Strategy):
    """Donchian Channel breakout with volume confirmation."""

    def __init__(
        self,
        channel_period: int = 20,
        volume_multiplier: float = 1.5,
        volume_period: int = 20,
        exit_period: int = 10,
        initial_capital: float = 10_000,
    ):
        super().__init__(initial_capital=initial_capital)
        self.channel_period = channel_period
        self.volume_multiplier = volume_multiplier
        self.volume_period = volume_period
        self.exit_period = exit_period

    @classmethod
    def meta(cls) -> StrategyMeta:
        return StrategyMeta(
            name="Breakout Strategy",
            slug="breakout",
            category="universal",
            description="Donchian Channel breakout with volume confirmation. Classic trend entry.",
            parameters={
                "channel_period": "Donchian channel lookback (default: 20)",
                "volume_multiplier": "Min volume ratio to confirm (default: 1.5)",
                "volume_period": "Volume SMA period (default: 20)",
                "exit_period": "Exit channel period (default: 10)",
            },
            usage_example="finclaw strategy backtest breakout --symbol AAPL --start 2024-01-01",
        )

    def generate_signals(self, data: list[dict[str, Any]]) -> list[StrategySignal]:
        signals: list[StrategySignal] = []
        highs = [bar.get("high", bar["close"]) for bar in data]
        lows = [bar.get("low", bar["close"]) for bar in data]
        in_position = False

        for i in range(len(data)):
            price = data[i]["close"]
            volume = data[i].get("volume", 0)

            if i < self.channel_period:
                signals.append(StrategySignal("hold", 0.0, price=price, reason="warming up"))
                continue

            ch = donchian_channel(highs[:i], lows[:i], self.channel_period)
            if ch is None:
                signals.append(StrategySignal("hold", 0.0, price=price, reason="insufficient data"))
                continue

            upper, mid, lower = ch

            # Volume confirmation
            vol_avg = sum(d.get("volume", 0) for d in data[max(0, i - self.volume_period):i]) / self.volume_period if i >= self.volume_period else 1
            vol_confirmed = volume >= vol_avg * self.volume_multiplier if vol_avg > 0 else True

            if not in_position and price > upper and vol_confirmed:
                signals.append(StrategySignal(
                    "buy", 0.8, price=price,
                    reason=f"breakout above {upper:.2f} with volume",
                    metadata={"channel_upper": upper, "volume_ratio": volume / vol_avg if vol_avg > 0 else 0},
                ))
                in_position = True
            elif in_position:
                exit_ch = donchian_channel(highs[:i], lows[:i], self.exit_period)
                if exit_ch and price < exit_ch[2]:
                    signals.append(StrategySignal(
                        "sell", 0.7, price=price,
                        reason=f"exit: broke below {exit_ch[2]:.2f}",
                    ))
                    in_position = False
                else:
                    signals.append(StrategySignal("hold", 0.0, price=price, reason="in position, holding"))
            else:
                signals.append(StrategySignal("hold", 0.0, price=price, reason="no breakout"))

        return signals
