"""
MACD Crossover Strategy
========================
Buy when MACD line crosses above signal line (bullish crossover).
Sell when MACD line crosses below signal line (bearish crossover).

Optionally filters trades using histogram momentum and zero-line position.

Parameters:
    fast_period: Fast EMA period (default: 12).
    slow_period: Slow EMA period (default: 26).
    signal_period: Signal line EMA period (default: 9).
    require_zero_cross: Only trade when MACD crosses zero line (default: False).
    histogram_filter: Require histogram momentum confirmation (default: True).

Usage:
    strategy = MACDCrossoverStrategy(fast_period=12, slow_period=26)
    signals = strategy.generate_signals(ohlcv_data)
"""

from __future__ import annotations
from typing import Any
from .base import Strategy, StrategySignal, StrategyMeta, ema


class MACDCrossoverStrategy(Strategy):
    """MACD crossover strategy with optional histogram momentum filter."""

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        require_zero_cross: bool = False,
        histogram_filter: bool = True,
        initial_capital: float = 10_000,
    ):
        super().__init__(initial_capital=initial_capital)
        if fast_period >= slow_period:
            raise ValueError("fast_period must be less than slow_period")
        if signal_period < 1:
            raise ValueError("signal_period must be >= 1")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.require_zero_cross = require_zero_cross
        self.histogram_filter = histogram_filter

    @classmethod
    def meta(cls) -> StrategyMeta:
        return StrategyMeta(
            name="MACD Crossover",
            slug="macd-crossover",
            category="universal",
            description="Buy on bullish MACD crossover, sell on bearish crossover. "
                        "Optionally filters by histogram momentum and zero-line.",
            parameters={
                "fast_period": "Fast EMA period (default: 12)",
                "slow_period": "Slow EMA period (default: 26)",
                "signal_period": "Signal line EMA period (default: 9)",
                "require_zero_cross": "Only trade on zero-line crosses (default: False)",
                "histogram_filter": "Require histogram momentum confirmation (default: True)",
            },
            usage_example="finclaw strategy backtest macd-crossover --symbol AAPL --start 2024-01-01",
        )

    def generate_signals(self, data: list[dict[str, Any]]) -> list[StrategySignal]:
        signals: list[StrategySignal] = []
        closes = [bar["close"] for bar in data]
        min_bars = self.slow_period + self.signal_period

        # Pre-compute MACD components incrementally
        macd_line: list[float | None] = []
        signal_line: list[float | None] = []
        histogram: list[float | None] = []

        for i in range(len(data)):
            if i < self.slow_period - 1:
                macd_line.append(None)
                signal_line.append(None)
                histogram.append(None)
                continue

            fast_ema = ema(closes[: i + 1], self.fast_period)
            slow_ema = ema(closes[: i + 1], self.slow_period)

            if fast_ema is None or slow_ema is None:
                macd_line.append(None)
                signal_line.append(None)
                histogram.append(None)
                continue

            ml = fast_ema - slow_ema
            macd_line.append(ml)

            # Signal line needs enough MACD values
            valid_macd = [v for v in macd_line if v is not None]
            if len(valid_macd) >= self.signal_period:
                sl = ema(valid_macd, self.signal_period)
                signal_line.append(sl)
                histogram.append(ml - sl if sl is not None else None)
            else:
                signal_line.append(None)
                histogram.append(None)

        # Generate signals from crossovers
        for i in range(len(data)):
            price = data[i]["close"]

            if i < min_bars or macd_line[i] is None or signal_line[i] is None:
                signals.append(StrategySignal("hold", 0.0, price=price, reason="warming up"))
                continue

            if macd_line[i - 1] is None or signal_line[i - 1] is None:
                signals.append(StrategySignal("hold", 0.0, price=price, reason="warming up"))
                continue

            curr_macd = macd_line[i]
            prev_macd = macd_line[i - 1]
            curr_signal = signal_line[i]
            prev_signal = signal_line[i - 1]
            curr_hist = histogram[i]
            prev_hist = histogram[i - 1] if histogram[i - 1] is not None else 0

            # Detect crossover
            bullish_cross = prev_macd <= prev_signal and curr_macd > curr_signal
            bearish_cross = prev_macd >= prev_signal and curr_macd < curr_signal

            # Optional: require zero-line cross
            if self.require_zero_cross:
                bullish_cross = bullish_cross and prev_macd <= 0 and curr_macd > 0
                bearish_cross = bearish_cross and prev_macd >= 0 and curr_macd < 0

            # Optional: histogram momentum filter
            hist_confirms_buy = True
            hist_confirms_sell = True
            if self.histogram_filter and curr_hist is not None and prev_hist is not None:
                hist_confirms_buy = curr_hist > prev_hist  # histogram expanding
                hist_confirms_sell = curr_hist < prev_hist  # histogram contracting

            metadata = {
                "macd": curr_macd,
                "signal": curr_signal,
                "histogram": curr_hist,
            }

            if bullish_cross and hist_confirms_buy:
                confidence = min(abs(curr_macd - curr_signal) / max(abs(curr_signal), 0.01) + 0.5, 1.0)
                signals.append(StrategySignal(
                    "buy", confidence, price=price,
                    reason=f"MACD bullish crossover (MACD={curr_macd:.4f}, Signal={curr_signal:.4f})",
                    metadata=metadata,
                ))
            elif bearish_cross and hist_confirms_sell:
                confidence = min(abs(curr_macd - curr_signal) / max(abs(curr_signal), 0.01) + 0.5, 1.0)
                signals.append(StrategySignal(
                    "sell", confidence, price=price,
                    reason=f"MACD bearish crossover (MACD={curr_macd:.4f}, Signal={curr_signal:.4f})",
                    metadata=metadata,
                ))
            else:
                signals.append(StrategySignal(
                    "hold", 0.0, price=price,
                    reason=f"No crossover (MACD={curr_macd:.4f}, Signal={curr_signal:.4f})",
                    metadata=metadata,
                ))

        return signals
