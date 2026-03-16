"""Slippage models for realistic backtesting.

Each static method returns a callable(price, quantity) -> adjusted_price.
"""

from __future__ import annotations

from typing import Callable, List


class SlippageModel:
    """Collection of slippage model factories."""

    @staticmethod
    def none() -> Callable[[float, float], float]:
        """No slippage — returns price unchanged."""
        return lambda price, qty: price

    @staticmethod
    def fixed(bps: float = 5) -> Callable[[float, float], float]:
        """Fixed basis-point slippage.

        Args:
            bps: Slippage in basis points (1 bp = 0.01%).
        """
        def _slippage(price: float, qty: float) -> float:
            direction = 1 if qty >= 0 else -1
            return price * (1 + direction * bps / 10_000)
        return _slippage

    @staticmethod
    def volume_based(impact_coeff: float = 0.1) -> Callable[[float, float], float]:
        """Volume-based market impact slippage.

        Slippage = impact_coeff * sqrt(|qty|) * price / 10000
        """
        def _slippage(price: float, qty: float) -> float:
            direction = 1 if qty >= 0 else -1
            impact = impact_coeff * (abs(qty) ** 0.5)
            return price * (1 + direction * impact / 10_000)
        return _slippage

    @staticmethod
    def spread_based(spread_pct: float = 0.02) -> Callable[[float, float], float]:
        """Bid-ask spread slippage.

        Args:
            spread_pct: Spread as a percentage of price (0.02 = 0.02%).
        """
        def _slippage(price: float, qty: float) -> float:
            direction = 1 if qty >= 0 else -1
            return price * (1 + direction * spread_pct / 100)
        return _slippage

    @staticmethod
    def composite(models: List[Callable[[float, float], float]]) -> Callable[[float, float], float]:
        """Chain multiple slippage models together.

        Each model's output price feeds into the next.
        """
        def _slippage(price: float, qty: float) -> float:
            p = price
            for model in models:
                p = model(p, qty)
            return p
        return _slippage
