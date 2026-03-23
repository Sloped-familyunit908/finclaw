"""
Factor: crypto_ema_ribbon
Description: Is EMA(6) > EMA(12) > EMA(24) > EMA(48)? (ribbon alignment)
Category: crypto
"""

FACTOR_NAME = "crypto_ema_ribbon"
FACTOR_DESC = "EMA ribbon alignment score"
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
    """Returns float in [0, 1]. 1.0 = perfect bullish alignment, 0.0 = perfect bearish."""
    if idx < 48:
        return 0.5

    ema6 = _ema(closes, 6, idx)
    ema12 = _ema(closes, 12, idx)
    ema24 = _ema(closes, 24, idx)
    ema48 = _ema(closes, 48, idx)

    emas = [ema6, ema12, ema24, ema48]

    # Count bullish pairs (shorter > longer)
    bullish_pairs = 0
    bearish_pairs = 0
    total_pairs = 0
    for i in range(len(emas)):
        for j in range(i + 1, len(emas)):
            total_pairs += 1
            if emas[i] > emas[j]:
                bullish_pairs += 1
            elif emas[i] < emas[j]:
                bearish_pairs += 1

    if total_pairs == 0:
        return 0.5

    score = bullish_pairs / total_pairs
    return max(0.0, min(1.0, score))
