"""
Trading signals — combine indicators into actionable signals.

All functions are zero-dependency, using only the builtin indicators module.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from .builtin import sma


def detect_golden_cross(
    prices: List[float],
    short_period: int = 50,
    long_period: int = 200,
) -> List[Optional[str]]:
    """Detect Golden Cross — SMA short crosses above SMA long.

    Returns a list of same length as *prices*. Each element is
    ``"golden_cross"`` at the crossover bar, else ``None``.
    """
    short_ma = sma(prices, short_period)
    long_ma = sma(prices, long_period)
    out: List[Optional[str]] = [None] * len(prices)
    for i in range(1, len(prices)):
        if (short_ma[i] is not None and long_ma[i] is not None
                and short_ma[i - 1] is not None and long_ma[i - 1] is not None):
            if short_ma[i - 1] <= long_ma[i - 1] and short_ma[i] > long_ma[i]:  # type: ignore
                out[i] = "golden_cross"
    return out


def detect_death_cross(
    prices: List[float],
    short_period: int = 50,
    long_period: int = 200,
) -> List[Optional[str]]:
    """Detect Death Cross — SMA short crosses below SMA long.

    Returns ``"death_cross"`` at the crossover bar, else ``None``.
    """
    short_ma = sma(prices, short_period)
    long_ma = sma(prices, long_period)
    out: List[Optional[str]] = [None] * len(prices)
    for i in range(1, len(prices)):
        if (short_ma[i] is not None and long_ma[i] is not None
                and short_ma[i - 1] is not None and long_ma[i - 1] is not None):
            if short_ma[i - 1] >= long_ma[i - 1] and short_ma[i] < long_ma[i]:  # type: ignore
                out[i] = "death_cross"
    return out


def detect_rsi_divergence(
    prices: List[float],
    rsi_values: List[Optional[float]],
    lookback: int = 14,
) -> List[Optional[str]]:
    """Detect RSI divergence (bullish and bearish).

    Bullish divergence: price makes lower low but RSI makes higher low.
    Bearish divergence: price makes higher high but RSI makes lower high.

    Scans windows of *lookback* bars. Returns ``"bullish_divergence"``
    or ``"bearish_divergence"`` at detection bar, else ``None``.
    """
    out: List[Optional[str]] = [None] * len(prices)
    for i in range(lookback, len(prices)):
        p_window = prices[i - lookback: i + 1]
        r_window = [v for v in rsi_values[i - lookback: i + 1] if v is not None]
        if len(r_window) < 2:
            continue

        p_min_idx = p_window.index(min(p_window))
        p_max_idx = p_window.index(max(p_window))

        # Bullish: price at new low, RSI not
        if p_min_idx == lookback and r_window[-1] > min(r_window):
            out[i] = "bullish_divergence"
        # Bearish: price at new high, RSI not
        elif p_max_idx == lookback and r_window[-1] < max(r_window):
            out[i] = "bearish_divergence"
    return out


def detect_macd_crossover(
    macd_line: List[float],
    signal_line: List[float],
) -> List[Optional[str]]:
    """Detect MACD crossovers.

    Returns ``"bullish_crossover"`` when MACD crosses above signal,
    ``"bearish_crossover"`` when below, else ``None``.
    """
    out: List[Optional[str]] = [None] * len(macd_line)
    for i in range(1, len(macd_line)):
        if macd_line[i - 1] <= signal_line[i - 1] and macd_line[i] > signal_line[i]:
            out[i] = "bullish_crossover"
        elif macd_line[i - 1] >= signal_line[i - 1] and macd_line[i] < signal_line[i]:
            out[i] = "bearish_crossover"
    return out


def detect_bollinger_squeeze(
    bands: Dict[str, List[Optional[float]]],
    threshold: float = 0.02,
) -> List[Optional[str]]:
    """Detect Bollinger Band squeeze (low volatility).

    A squeeze occurs when bandwidth < *threshold*.
    Returns ``"squeeze"`` at those bars, else ``None``.
    """
    bw = bands["bandwidth"]
    out: List[Optional[str]] = [None] * len(bw)
    for i, val in enumerate(bw):
        if val is not None and val < threshold:
            out[i] = "squeeze"
    return out
