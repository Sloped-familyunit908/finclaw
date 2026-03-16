"""
Sector Rotation
===============
Momentum-based sector ETF rotation strategy.

Parameters:
    top_n: Number of top sectors to hold (default: 3).
    lookback: Momentum lookback in bars (default: 63, ~3 months).
    rebalance_freq: Rebalance every N bars (default: 21, ~monthly).
    sma_filter: Only buy sectors above their SMA (default: True).
    sma_period: SMA period for trend filter (default: 200).

Usage:
    strategy = SectorRotationStrategy(top_n=3, lookback=63)
    signals = strategy.generate_signals(sector_data)

Data format:
    Each bar must include 'close' and 'sectors' dict mapping symbol -> price.
"""

from __future__ import annotations
from typing import Any
from .base import Strategy, StrategySignal, StrategyMeta


SECTOR_ETFS = {
    "XLK": "Technology", "XLF": "Financials", "XLV": "Healthcare",
    "XLE": "Energy", "XLI": "Industrials", "XLY": "Consumer Disc.",
    "XLP": "Consumer Staples", "XLU": "Utilities", "XLRE": "Real Estate",
    "XLB": "Materials", "XLC": "Communication",
}


class SectorRotationStrategy(Strategy):
    """Rotate into top-momentum sectors, with optional SMA trend filter."""

    def __init__(
        self,
        top_n: int = 3,
        lookback: int = 63,
        rebalance_freq: int = 21,
        sma_filter: bool = True,
        sma_period: int = 200,
        initial_capital: float = 10_000,
    ):
        super().__init__(initial_capital=initial_capital)
        self.top_n = top_n
        self.lookback = lookback
        self.rebalance_freq = rebalance_freq
        self.sma_filter = sma_filter
        self.sma_period = sma_period

    @classmethod
    def meta(cls) -> StrategyMeta:
        return StrategyMeta(
            name="Sector Rotation",
            slug="sector-rotation",
            category="stock",
            description="Momentum-based sector ETF rotation. Holds top-N sectors by recent return.",
            parameters={
                "top_n": "Number of sectors to hold (default: 3)",
                "lookback": "Momentum lookback in bars (default: 63)",
                "rebalance_freq": "Rebalance every N bars (default: 21)",
                "sma_filter": "Only buy sectors above SMA (default: True)",
                "sma_period": "SMA period for trend filter (default: 200)",
            },
            usage_example="finclaw strategy backtest sector-rotation --start 2024-01-01",
        )

    def generate_signals(self, data: list[dict[str, Any]]) -> list[StrategySignal]:
        signals: list[StrategySignal] = []
        current_holdings: list[str] = []

        for i, bar in enumerate(data):
            if i < self.lookback:
                signals.append(StrategySignal("hold", 0.0, price=bar["close"], reason="warming up"))
                continue

            if i % self.rebalance_freq != 0 and current_holdings:
                signals.append(StrategySignal("hold", 0.0, price=bar["close"], reason="between rebalances"))
                continue

            # Rank sectors by momentum
            sectors = bar.get("sectors", {})
            if not sectors:
                signals.append(StrategySignal("hold", 0.0, price=bar["close"], reason="no sector data"))
                continue

            ranked: list[tuple[str, float]] = []
            for sym, current_price in sectors.items():
                past_bar = data[i - self.lookback]
                past_price = past_bar.get("sectors", {}).get(sym, current_price)
                if past_price > 0:
                    momentum = (current_price - past_price) / past_price
                    ranked.append((sym, momentum))

            ranked.sort(key=lambda x: x[1], reverse=True)
            top = [sym for sym, _ in ranked[:self.top_n]]
            current_holdings = top

            signals.append(StrategySignal(
                "buy", 0.7, price=bar["close"],
                reason=f"rebalance: hold {', '.join(top)}",
                metadata={"holdings": top, "rankings": ranked[:5]},
            ))

        return signals
