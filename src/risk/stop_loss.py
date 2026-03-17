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


class ChandelierExit:
    """
    Chandelier Exit — trailing stop based on ATR from the highest high.

    Stop = Highest High(N) - multiplier * ATR(N)
    """

    def __init__(self, period: int = 22, multiplier: float = 3.0):
        self.period = period
        self.multiplier = multiplier

    def compute(
        self,
        highs: list[float],
        lows: list[float],
        closes: list[float],
    ) -> list[float]:
        """
        Compute chandelier exit levels for the full series.

        Args:
            highs: List of high prices.
            lows: List of low prices.
            closes: List of close prices.

        Returns:
            List of stop levels (NaN for insufficient data).
        """
        n = len(closes)
        if n < self.period + 1:
            return [float('nan')] * n

        # Compute ATR
        trs = [highs[0] - lows[0]]
        for i in range(1, n):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            trs.append(tr)

        stops = [float('nan')] * n
        for i in range(self.period, n):
            atr = sum(trs[i - self.period + 1:i + 1]) / self.period
            highest = max(highs[i - self.period + 1:i + 1])
            stops[i] = highest - self.multiplier * atr

        return stops


class ParabolicSARStop:
    """
    Parabolic SAR — accelerating trailing stop.

    Simplified implementation for stop-loss purposes.
    """

    def __init__(
        self,
        af_start: float = 0.02,
        af_step: float = 0.02,
        af_max: float = 0.20,
    ):
        self.af_start = af_start
        self.af_step = af_step
        self.af_max = af_max

    def compute(
        self,
        highs: list[float],
        lows: list[float],
    ) -> list[float]:
        """
        Compute Parabolic SAR values.

        Args:
            highs: High prices.
            lows: Low prices.

        Returns:
            List of SAR values.
        """
        n = len(highs)
        if n < 2:
            return [float('nan')] * n

        sar = [0.0] * n
        af = self.af_start
        uptrend = True
        ep = highs[0]  # extreme point
        sar[0] = lows[0]

        for i in range(1, n):
            if uptrend:
                sar[i] = sar[i - 1] + af * (ep - sar[i - 1])
                sar[i] = min(sar[i], lows[i - 1])
                if i >= 2:
                    sar[i] = min(sar[i], lows[i - 2])
                if lows[i] < sar[i]:
                    uptrend = False
                    sar[i] = ep
                    ep = lows[i]
                    af = self.af_start
                else:
                    if highs[i] > ep:
                        ep = highs[i]
                        af = min(af + self.af_step, self.af_max)
            else:
                sar[i] = sar[i - 1] + af * (ep - sar[i - 1])
                sar[i] = max(sar[i], highs[i - 1])
                if i >= 2:
                    sar[i] = max(sar[i], highs[i - 2])
                if highs[i] > sar[i]:
                    uptrend = True
                    sar[i] = ep
                    ep = highs[i]
                    af = self.af_start
                else:
                    if lows[i] < ep:
                        ep = lows[i]
                        af = min(af + self.af_step, self.af_max)

        return sar


class BreakEvenStop:
    """
    Break-even stop — move stop to entry price after a target profit %.

    Protects gains by ensuring no loss once the trade moves in your favor.
    """

    def __init__(self, trigger_pct: float = 0.03, buffer_pct: float = 0.001):
        """
        Args:
            trigger_pct: Profit % threshold to activate (e.g. 0.03 = 3%).
            buffer_pct: Small buffer above entry to cover fees (e.g. 0.001 = 0.1%).
        """
        self.trigger_pct = trigger_pct
        self.buffer_pct = buffer_pct

    def get_stop(
        self,
        entry_price: float,
        current_price: float,
        original_stop: float,
    ) -> float:
        """
        Compute the stop level.

        Returns the original stop if profit hasn't reached trigger,
        otherwise returns entry + buffer.

        Args:
            entry_price: Trade entry price.
            current_price: Current market price.
            original_stop: The original stop-loss price.

        Returns:
            Stop price.
        """
        if entry_price <= 0:
            return original_stop
        profit_pct = (current_price - entry_price) / entry_price
        if profit_pct >= self.trigger_pct:
            return entry_price * (1 + self.buffer_pct)
        return original_stop
