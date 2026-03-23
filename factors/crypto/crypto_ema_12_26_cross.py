"""
Factor: crypto_ema_12_26_cross
Description: EMA(12) vs EMA(26) position and recency of cross
Category: crypto
"""

FACTOR_NAME = "crypto_ema_12_26_cross"
FACTOR_DESC = "EMA(12) vs EMA(26) crossover signal"
FACTOR_CATEGORY = "crypto"


def _ema(data, period, end_idx):
    """Compute EMA ending at end_idx."""
    if end_idx < period:
        return sum(data[:end_idx + 1]) / (end_idx + 1) if end_idx >= 0 else 0
    k = 2.0 / (period + 1)
    start = end_idx - period * 3
    if start < 0:
        start = 0
    val = sum(data[start:start + period]) / period
    for i in range(start + period, end_idx + 1):
        val = data[i] * k + val * (1 - k)
    return val


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Above 0.5 = EMA12 above EMA26 (bullish)."""
    if idx < 26:
        return 0.5

    ema12 = _ema(closes, 12, idx)
    ema26 = _ema(closes, 26, idx)

    if ema26 <= 0:
        return 0.5

    diff_pct = (ema12 - ema26) / ema26

    # Check for recency of cross
    cross_bonus = 0.0
    prev_ema12 = _ema(closes, 12, idx - 1)
    prev_ema26 = _ema(closes, 26, idx - 1)
    if (prev_ema12 <= prev_ema26 and ema12 > ema26):
        cross_bonus = 0.1  # Just crossed up
    elif (prev_ema12 >= prev_ema26 and ema12 < ema26):
        cross_bonus = -0.1  # Just crossed down

    score = 0.5 + (diff_pct / 0.04) * 0.4 + cross_bonus
    return max(0.0, min(1.0, score))
