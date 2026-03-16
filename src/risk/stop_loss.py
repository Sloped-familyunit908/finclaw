"""
Stop-Loss Manager
Fixed, trailing, ATR-based, and time-based stop losses.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class StopLossType(Enum):
    FIXED = "fixed"
    TRAILING = "trailing"
    ATR = "atr"
    TIME = "time"


@dataclass
class StopLevel:
    price: float
    type: StopLossType
    triggered: bool = False
    reason: str = ""


class StopLossManager:
    """Manages multiple stop-loss types simultaneously."""

    def __init__(
        self,
        fixed_pct: float = 0.05,
        trailing_pct: float = 0.08,
        atr_multiplier: float = 2.0,
        max_hold_bars: int = 60,
    ):
        self.fixed_pct = fixed_pct
        self.trailing_pct = trailing_pct
        self.atr_multiplier = atr_multiplier
        self.max_hold_bars = max_hold_bars

    def compute_stops(
        self,
        entry_price: float,
        current_price: float,
        highest_since_entry: float,
        bars_held: int,
        atr: Optional[float] = None,
    ) -> list[StopLevel]:
        """Compute all stop levels and check if any triggered."""
        stops = []

        # Fixed stop
        fixed_stop = entry_price * (1 - self.fixed_pct)
        stops.append(StopLevel(
            price=fixed_stop,
            type=StopLossType.FIXED,
            triggered=current_price <= fixed_stop,
            reason=f"fixed {self.fixed_pct:.0%} below entry",
        ))

        # Trailing stop
        trail_stop = highest_since_entry * (1 - self.trailing_pct)
        stops.append(StopLevel(
            price=trail_stop,
            type=StopLossType.TRAILING,
            triggered=current_price <= trail_stop,
            reason=f"trailing {self.trailing_pct:.0%} from peak {highest_since_entry:.2f}",
        ))

        # ATR-based stop
        if atr is not None and atr > 0:
            atr_stop = current_price - self.atr_multiplier * atr
            stops.append(StopLevel(
                price=atr_stop,
                type=StopLossType.ATR,
                triggered=current_price <= atr_stop,
                reason=f"{self.atr_multiplier}x ATR ({atr:.2f})",
            ))

        # Time-based stop
        stops.append(StopLevel(
            price=current_price,  # exit at market
            type=StopLossType.TIME,
            triggered=bars_held >= self.max_hold_bars,
            reason=f"held {bars_held}/{self.max_hold_bars} bars",
        ))

        return stops

    def get_tightest_stop(self, stops: list[StopLevel]) -> Optional[StopLevel]:
        """Get the highest (tightest) stop level."""
        price_stops = [s for s in stops if s.type != StopLossType.TIME]
        if not price_stops:
            return None
        return max(price_stops, key=lambda s: s.price)

    def any_triggered(self, stops: list[StopLevel]) -> Optional[StopLevel]:
        """Return the first triggered stop, or None."""
        for s in stops:
            if s.triggered:
                return s
        return None
