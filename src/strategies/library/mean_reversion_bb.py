"""
Mean Reversion — Bollinger Bands + RSI
=======================================
Buy when price touches lower BB and RSI confirms oversold.

Parameters:
    bb_period: Bollinger Bands period (default: 20).
    bb_std: Number of standard deviations (default: 2.0).
    rsi_period: RSI period (default: 14).
    rsi_oversold: RSI oversold threshold (default: 30).
    rsi_overbought: RSI overbought threshold (default: 70).

Usage:
    strategy = MeanReversionBBStrategy(bb_period=20, rsi_oversold=25)
    signals = strategy.generate_signals(ohlcv_data)
"""

from __future__ import annotations
from typing import Any
from .base import Strategy, StrategySignal, StrategyMeta, rsi as calc_rsi, bollinger_bands


class MeanReversionBBStrategy(Strategy):
    """Mean reversion using Bollinger Bands + RSI confirmation."""

    def __init__(
        self,
        bb_period: int = 20,
        bb_std: float = 2.0,
        rsi_period: int = 14,
        rsi_oversold: float = 30.0,
        rsi_overbought: float = 70.0,
        initial_capital: float = 10_000,
    ):
        super().__init__(initial_capital=initial_capital)
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought

    @classmethod
    def meta(cls) -> StrategyMeta:
        return StrategyMeta(
            name="Mean Reversion (Bollinger Bands)",
            slug="mean-reversion-bb",
            category="universal",
            description="Buy at lower Bollinger Band with RSI oversold confirmation. Sell at upper BB.",
            parameters={
                "bb_period": "Bollinger Bands period (default: 20)",
                "bb_std": "Number of std deviations (default: 2.0)",
                "rsi_period": "RSI period (default: 14)",
                "rsi_oversold": "RSI buy threshold (default: 30)",
                "rsi_overbought": "RSI sell threshold (default: 70)",
            },
            usage_example="finclaw strategy backtest mean-reversion-bb --symbol SPY --start 2024-01-01",
        )

    def generate_signals(self, data: list[dict[str, Any]]) -> list[StrategySignal]:
        signals: list[StrategySignal] = []
        closes = [bar["close"] for bar in data]
        min_bars = max(self.bb_period, self.rsi_period + 1)

        for i in range(len(data)):
            price = data[i]["close"]
            if i < min_bars:
                signals.append(StrategySignal("hold", 0.0, price=price, reason="warming up"))
                continue

            bb = bollinger_bands(closes[: i + 1], self.bb_period, self.bb_std)
            rsi_val = calc_rsi(closes[: i + 1], self.rsi_period)

            if bb is None or rsi_val is None:
                signals.append(StrategySignal("hold", 0.0, price=price, reason="insufficient data"))
                continue

            upper, mid, lower = bb
            bb_range = upper - lower if upper != lower else 1
            bb_pos = (price - lower) / bb_range

            # Buy: price near lower BB + RSI oversold
            if price <= lower and rsi_val < self.rsi_oversold:
                signals.append(StrategySignal(
                    "buy", min((self.rsi_oversold - rsi_val) / 30 + 0.5, 1.0), price=price,
                    reason=f"at lower BB ({lower:.2f}), RSI={rsi_val:.1f}",
                    metadata={"bb_position": bb_pos, "rsi": rsi_val},
                ))
            # Sell: price near upper BB + RSI overbought
            elif price >= upper and rsi_val > self.rsi_overbought:
                signals.append(StrategySignal(
                    "sell", min((rsi_val - self.rsi_overbought) / 30 + 0.5, 1.0), price=price,
                    reason=f"at upper BB ({upper:.2f}), RSI={rsi_val:.1f}",
                    metadata={"bb_position": bb_pos, "rsi": rsi_val},
                ))
            else:
                signals.append(StrategySignal(
                    "hold", 0.0, price=price,
                    reason=f"BB pos={bb_pos:.2f}, RSI={rsi_val:.1f}",
                    metadata={"bb_position": bb_pos, "rsi": rsi_val},
                ))

        return signals
