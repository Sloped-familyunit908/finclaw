"""
Grid Trading Bot
================
Range-based buy/sell grid strategy for sideways/range-bound markets.

Parameters:
    lower_price: Lower bound of the grid range.
    upper_price: Upper bound of the grid range.
    num_grids: Number of grid levels (default: 10).
    initial_capital: Starting capital (default: 10000).

Usage:
    strategy = GridTradingStrategy(lower_price=25000, upper_price=35000, num_grids=15)
    signals = strategy.generate_signals(ohlcv_data)
    result = strategy.backtest(ohlcv_data)
"""

from __future__ import annotations
from typing import Any
from .base import Strategy, StrategySignal, StrategyMeta


class GridTradingStrategy(Strategy):
    """Grid Trading Bot — places buy/sell orders at evenly spaced price levels."""

    def __init__(
        self,
        lower_price: float = 25_000,
        upper_price: float = 35_000,
        num_grids: int = 10,
        initial_capital: float = 10_000,
    ):
        super().__init__(initial_capital=initial_capital)
        if lower_price >= upper_price:
            raise ValueError("lower_price must be < upper_price")
        if num_grids < 2:
            raise ValueError("num_grids must be >= 2")
        self.lower_price = lower_price
        self.upper_price = upper_price
        self.num_grids = num_grids
        self.grid_levels = self._build_grid()
        self.filled_buys: set[int] = set()
        self.filled_sells: set[int] = set()

    @classmethod
    def meta(cls) -> StrategyMeta:
        return StrategyMeta(
            name="Grid Trading Bot",
            slug="grid-trading",
            category="crypto",
            description="Range-based buy/sell grid for sideways markets. Places orders at evenly spaced levels.",
            parameters={
                "lower_price": "Lower bound of grid range",
                "upper_price": "Upper bound of grid range",
                "num_grids": "Number of grid levels (default: 10)",
            },
            usage_example="finclaw strategy backtest grid-trading --symbol BTCUSDT --start 2024-01-01",
        )

    def _build_grid(self) -> list[float]:
        step = (self.upper_price - self.lower_price) / self.num_grids
        return [round(self.lower_price + i * step, 8) for i in range(self.num_grids + 1)]

    def generate_signals(self, data: list[dict[str, Any]]) -> list[StrategySignal]:
        signals: list[StrategySignal] = []
        prev_price: float | None = None

        for bar in data:
            price = bar["close"]
            sig = StrategySignal("hold", 0.0, price=price, reason="no grid crossed")

            if prev_price is not None:
                for idx, level in enumerate(self.grid_levels):
                    if prev_price >= level > price and idx not in self.filled_buys:
                        sig = StrategySignal("buy", 0.8, price=level, reason=f"crossed below grid {idx} @ {level}")
                        self.filled_buys.add(idx)
                        self.filled_sells.discard(idx)
                        break
                    if prev_price <= level < price and idx not in self.filled_sells:
                        sig = StrategySignal("sell", 0.8, price=level, reason=f"crossed above grid {idx} @ {level}")
                        self.filled_sells.add(idx)
                        self.filled_buys.discard(idx)
                        break

            prev_price = price
            signals.append(sig)

        return signals
