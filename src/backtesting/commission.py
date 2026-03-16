"""Commission models for realistic backtesting.

Each static method returns a callable(price, quantity) -> commission_amount.
"""

from __future__ import annotations

from typing import Callable, List, Tuple


class CommissionModel:
    """Collection of commission model factories."""

    @staticmethod
    def zero() -> Callable[[float, float], float]:
        """No commission."""
        return lambda price, qty: 0.0

    @staticmethod
    def fixed(amount: float = 1.0) -> Callable[[float, float], float]:
        """Fixed commission per trade.

        Args:
            amount: Flat fee per trade in currency units.
        """
        return lambda price, qty: amount

    @staticmethod
    def percentage(rate: float = 0.001) -> Callable[[float, float], float]:
        """Percentage-based commission.

        Args:
            rate: Commission rate (0.001 = 0.1%).
        """
        def _commission(price: float, qty: float) -> float:
            return abs(price * qty) * rate
        return _commission

    @staticmethod
    def per_share(rate: float = 0.005, minimum: float = 1.0) -> Callable[[float, float], float]:
        """Per-share commission with minimum.

        Args:
            rate: Cost per share.
            minimum: Minimum commission per trade.
        """
        def _commission(price: float, qty: float) -> float:
            return max(abs(qty) * rate, minimum)
        return _commission

    @staticmethod
    def tiered(tiers: List[Tuple[float, float]]) -> Callable[[float, float], float]:
        """Tiered commission based on trade value.

        Args:
            tiers: List of (threshold, rate) tuples, sorted ascending by threshold.
                   Example: [(10000, 0.002), (50000, 0.0015), (float('inf'), 0.001)]
                   For value <= 10000: rate = 0.2%
                   For value <= 50000: rate = 0.15%
                   Above: rate = 0.1%
        """
        def _commission(price: float, qty: float) -> float:
            value = abs(price * qty)
            for threshold, rate in sorted(tiers):
                if value <= threshold:
                    return value * rate
            # If somehow exceeds all tiers, use last rate
            return value * tiers[-1][1] if tiers else 0.0
        return _commission

    @staticmethod
    def interactive_brokers() -> Callable[[float, float], float]:
        """Interactive Brokers US equity tiered commission model.

        IB tiered: $0.0035/share, min $0.35, max 1% of trade value.
        """
        def _commission(price: float, qty: float) -> float:
            shares = abs(qty)
            raw = shares * 0.0035
            minimum = 0.35
            maximum = abs(price * qty) * 0.01
            return max(min(raw, maximum), minimum)
        return _commission
