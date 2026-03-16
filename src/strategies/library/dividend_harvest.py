"""
Dividend Capture Strategy
=========================
Buy before ex-dividend date, sell after to capture the dividend.

Parameters:
    hold_days_before: Days to buy before ex-div (default: 2).
    hold_days_after: Days to hold after ex-div (default: 3).
    min_yield: Minimum dividend yield % to consider (default: 1.0).

Usage:
    strategy = DividendHarvestStrategy(hold_days_before=2, hold_days_after=3)
    signals = strategy.generate_signals(data_with_dividends)

Data format:
    Each bar should include 'close' and optionally 'dividend' (amount if ex-div day, else 0).
"""

from __future__ import annotations
from typing import Any
from .base import Strategy, StrategySignal, StrategyMeta


class DividendHarvestStrategy(Strategy):
    """Buy before ex-dividend, sell after to capture dividend payments."""

    def __init__(
        self,
        hold_days_before: int = 2,
        hold_days_after: int = 3,
        min_yield: float = 1.0,
        initial_capital: float = 10_000,
    ):
        super().__init__(initial_capital=initial_capital)
        self.hold_days_before = hold_days_before
        self.hold_days_after = hold_days_after
        self.min_yield = min_yield

    @classmethod
    def meta(cls) -> StrategyMeta:
        return StrategyMeta(
            name="Dividend Capture",
            slug="dividend-harvest",
            category="stock",
            description="Buy before ex-dividend date, hold through, sell after to capture dividend.",
            parameters={
                "hold_days_before": "Days before ex-div to buy (default: 2)",
                "hold_days_after": "Days after ex-div to sell (default: 3)",
                "min_yield": "Min dividend yield % to trade (default: 1.0)",
            },
            usage_example="finclaw strategy backtest dividend-harvest --symbol JNJ --start 2024-01-01",
        )

    def generate_signals(self, data: list[dict[str, Any]]) -> list[StrategySignal]:
        signals: list[StrategySignal] = []
        # Find ex-dividend days
        ex_div_days: list[int] = []
        for i, bar in enumerate(data):
            div = bar.get("dividend", 0)
            if div > 0:
                div_yield = (div / bar["close"]) * 100 if bar["close"] > 0 else 0
                if div_yield >= self.min_yield:
                    ex_div_days.append(i)

        # Build buy/sell zones
        buy_days: set[int] = set()
        sell_days: set[int] = set()
        for ed in ex_div_days:
            for d in range(max(0, ed - self.hold_days_before), ed):
                buy_days.add(d)
            for d in range(ed, min(len(data), ed + self.hold_days_after + 1)):
                sell_days.add(d)

        in_position = False
        for i, bar in enumerate(data):
            price = bar["close"]
            if i in buy_days and not in_position:
                signals.append(StrategySignal("buy", 0.7, price=price, reason="buy before ex-div"))
                in_position = True
            elif i in sell_days and in_position and i not in buy_days:
                signals.append(StrategySignal("sell", 0.7, price=price, reason="sell after ex-div"))
                in_position = False
            else:
                signals.append(StrategySignal("hold", 0.0, price=price, reason="no dividend event"))

        return signals
