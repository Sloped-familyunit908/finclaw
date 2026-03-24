"""
Factor: trend_momentum_confirmation
Description: Price trend, volume trend, and MACD all agree — triple confirmation
Category: trend_following
"""

FACTOR_NAME = "trend_momentum_confirmation"
FACTOR_DESC = "Price + volume + MACD all aligned bullish — triple confirmation"
FACTOR_CATEGORY = "trend_following"


def _calc_ema(closes, end_idx, period):
    """Calculate EMA at a given index."""
    if end_idx < period:
        return sum(closes[:end_idx + 1]) / (end_idx + 1)
    multiplier = 2.0 / (period + 1)
    ema = sum(closes[:period]) / period
    for i in range(period, end_idx + 1):
        ema = (closes[i] - ema) * multiplier + ema
    return ema


def compute(closes, highs, lows, volumes, idx):
    """Triple confirmation: price trend + volume trend + MACD all agree.
    Score based on how many signals are aligned bullish.
    """
    if idx < 30:
        return 0.5

    signals = 0
    total_signals = 3

    # 1. Price trend: close > 10-day MA
    ma10 = sum(closes[idx - 9 : idx + 1]) / 10
    if closes[idx] > ma10:
        signals += 1

    # 2. Volume trend: recent volume > average (last 5 > last 20)
    vol_5 = sum(volumes[idx - 4 : idx + 1]) / 5
    vol_20 = sum(volumes[idx - 19 : idx + 1]) / 20
    if vol_20 > 0 and vol_5 > vol_20:
        signals += 1

    # 3. MACD: EMA12 - EMA26 > signal line (EMA9 of MACD)
    ema12 = _calc_ema(closes, idx, 12)
    ema26 = _calc_ema(closes, idx, 26)
    macd = ema12 - ema26

    # Simple signal line approximation: MACD 1 day ago
    ema12_prev = _calc_ema(closes, idx - 1, 12)
    ema26_prev = _calc_ema(closes, idx - 1, 26)
    macd_prev = ema12_prev - ema26_prev

    if macd > 0 and macd > macd_prev:
        signals += 1  # MACD positive and rising

    # Score based on alignment
    score = signals / total_signals

    return max(0.0, min(1.0, score))
