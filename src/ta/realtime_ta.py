"""
FinClaw - Real-time Technical Analysis
Incremental indicator computation — update with each new tick
without recomputing full history.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class _EMAState:
    """Running EMA state."""
    period: int
    alpha: float = 0.0
    value: float = float('nan')
    count: int = 0

    def __post_init__(self):
        self.alpha = 2.0 / (self.period + 1)

    def update(self, price: float) -> float:
        if self.count == 0:
            self.value = price
        else:
            self.value = self.alpha * price + (1 - self.alpha) * self.value
        self.count += 1
        return self.value


@dataclass
class _RSIState:
    """Running RSI state using Wilder's smoothing."""
    period: int
    avg_gain: float = 0.0
    avg_loss: float = 0.0
    prev_price: float = float('nan')
    count: int = 0
    value: float = float('nan')

    def update(self, price: float) -> float:
        if self.count == 0:
            self.prev_price = price
            self.count += 1
            self.value = 50.0  # neutral on first tick
            return self.value

        delta = price - self.prev_price
        gain = max(delta, 0.0)
        loss = max(-delta, 0.0)
        self.prev_price = price

        if self.count <= self.period:
            # Accumulation phase
            self.avg_gain += gain / self.period
            self.avg_loss += loss / self.period
        else:
            # Wilder's smoothing
            self.avg_gain = (self.avg_gain * (self.period - 1) + gain) / self.period
            self.avg_loss = (self.avg_loss * (self.period - 1) + loss) / self.period

        self.count += 1
        if self.avg_loss == 0:
            self.value = 100.0 if self.avg_gain > 0 else 50.0
        else:
            rs = self.avg_gain / self.avg_loss
            self.value = 100.0 - 100.0 / (1.0 + rs)
        return self.value


@dataclass
class _MACDState:
    """Running MACD state."""
    fast_ema: _EMAState
    slow_ema: _EMAState
    signal_ema: _EMAState
    line: float = 0.0
    signal: float = 0.0
    histogram: float = 0.0

    def update(self, price: float) -> dict:
        fast = self.fast_ema.update(price)
        slow = self.slow_ema.update(price)
        self.line = fast - slow
        self.signal = self.signal_ema.update(self.line)
        self.histogram = self.line - self.signal
        return {'macd_line': self.line, 'macd_signal': self.signal, 'macd_histogram': self.histogram}


@dataclass
class _VWAPState:
    """Running VWAP state."""
    cum_volume: float = 0.0
    cum_tp_volume: float = 0.0
    value: float = 0.0

    def update(self, price: float, volume: float) -> float:
        self.cum_volume += volume
        self.cum_tp_volume += price * volume
        self.value = self.cum_tp_volume / self.cum_volume if self.cum_volume > 0 else price
        return self.value

    def reset(self) -> None:
        """Reset for new session/day."""
        self.cum_volume = 0.0
        self.cum_tp_volume = 0.0
        self.value = 0.0


@dataclass
class _BollingerState:
    """Running Bollinger Bands using a circular buffer."""
    period: int
    prices: list[float] = field(default_factory=list)
    upper: float = 0.0
    middle: float = 0.0
    lower: float = 0.0

    def update(self, price: float, num_std: float = 2.0) -> dict:
        self.prices.append(price)
        if len(self.prices) > self.period:
            self.prices.pop(0)

        n = len(self.prices)
        self.middle = sum(self.prices) / n
        if n < 2:
            self.upper = self.middle
            self.lower = self.middle
        else:
            var = sum((p - self.middle) ** 2 for p in self.prices) / n
            std = math.sqrt(var)
            self.upper = self.middle + num_std * std
            self.lower = self.middle - num_std * std

        return {'bb_upper': self.upper, 'bb_middle': self.middle, 'bb_lower': self.lower}


SUPPORTED_INDICATORS = ('ema', 'rsi', 'macd', 'vwap', 'bollinger')


class RealtimeTA:
    """
    Incremental technical analysis — feed one price at a time,
    get updated indicator values without recomputing full history.

    Usage:
        ta = RealtimeTA(['rsi', 'macd', 'ema'])
        for tick in stream:
            values = ta.update(tick.price, tick.volume)
            print(values)  # {'rsi': 55.2, 'macd_line': 0.5, ...}
    """

    def __init__(
        self,
        indicators: list[str],
        ema_period: int = 20,
        rsi_period: int = 14,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        bb_period: int = 20,
    ):
        self.indicators = [i.lower() for i in indicators]
        self.state: dict[str, any] = {}
        self._tick_count = 0

        for ind in self.indicators:
            if ind not in SUPPORTED_INDICATORS:
                raise ValueError(f"Unsupported indicator: {ind}. Use one of {SUPPORTED_INDICATORS}")

        if 'ema' in self.indicators:
            self.state['ema'] = _EMAState(period=ema_period)
        if 'rsi' in self.indicators:
            self.state['rsi'] = _RSIState(period=rsi_period)
        if 'macd' in self.indicators:
            self.state['macd'] = _MACDState(
                fast_ema=_EMAState(period=macd_fast),
                slow_ema=_EMAState(period=macd_slow),
                signal_ema=_EMAState(period=macd_signal),
            )
        if 'vwap' in self.indicators:
            self.state['vwap'] = _VWAPState()
        if 'bollinger' in self.indicators:
            self.state['bollinger'] = _BollingerState(period=bb_period)

    def update(self, price: float, volume: float = 0.0) -> dict:
        """
        Feed a new price tick and get updated indicator values.

        Args:
            price: Current price
            volume: Current volume (needed for VWAP)

        Returns:
            Dict of indicator name → value(s)
        """
        self._tick_count += 1
        result: dict[str, float] = {}

        if 'ema' in self.state:
            result['ema'] = self.state['ema'].update(price)

        if 'rsi' in self.state:
            result['rsi'] = self.state['rsi'].update(price)

        if 'macd' in self.state:
            macd_vals = self.state['macd'].update(price)
            result.update(macd_vals)

        if 'vwap' in self.state:
            result['vwap'] = self.state['vwap'].update(price, volume)

        if 'bollinger' in self.state:
            bb_vals = self.state['bollinger'].update(price)
            result.update(bb_vals)

        return result

    def reset(self) -> None:
        """Reset all indicator state (e.g. for a new trading session)."""
        indicators = self.indicators.copy()
        self.__init__(indicators)

    @property
    def tick_count(self) -> int:
        return self._tick_count
