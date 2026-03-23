"""
Factor: crypto_range_expansion_rate
Description: Rate at which candle ranges are expanding
Category: crypto
"""

FACTOR_NAME = "crypto_range_expansion_rate"
FACTOR_DESC = "Rate at which candle ranges are expanding"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. >0.5 = ranges expanding, <0.5 = contracting."""
    lookback = 24
    if idx < lookback:
        return 0.5

    recent = []
    older = []
    half = lookback // 2
    for i in range(idx - lookback, idx - half):
        older.append(highs[i] - lows[i])
    for i in range(idx - half, idx):
        recent.append(highs[i] - lows[i])

    avg_old = sum(older) / len(older) if older else 0
    avg_recent = sum(recent) / len(recent) if recent else 0

    if avg_old <= 0:
        return 0.5

    ratio = avg_recent / avg_old
    score = 0.5 + (ratio - 1.0) * 0.25
    return max(0.0, min(1.0, score))
