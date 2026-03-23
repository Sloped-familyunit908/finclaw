"""
Factor: crypto_lower_low_count
Description: Count of lower lows in last 24 bars — downtrend strength
Category: crypto
"""

FACTOR_NAME = "crypto_lower_low_count"
FACTOR_DESC = "Number of lower lows in last 24 bars — measures downtrend quality"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Low = many lower lows (strong downtrend)."""
    lookback = 24
    if idx < lookback:
        return 0.5

    count = 0
    for i in range(idx - lookback + 1, idx + 1):
        if lows[i] < lows[i - 1]:
            count += 1

    # Normalize: more lower lows = bearish = lower score
    ratio = count / lookback
    score = 1.0 - ratio  # Invert so lower lows = lower score
    return max(0.0, min(1.0, score))
