"""
Factor: crypto_consolidation_length
Description: Number of bars with <1% range (coiling for breakout)
Category: crypto
"""

FACTOR_NAME = "crypto_consolidation_length"
FACTOR_DESC = "Number of bars with <1% range (coiling for breakout)"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = long consolidation (breakout likely)."""
    lookback = 24
    if idx < lookback:
        return 0.5

    narrow_count = 0
    for i in range(idx - lookback, idx):
        if closes[i] <= 0:
            continue
        bar_range = (highs[i] - lows[i]) / closes[i]
        if bar_range < 0.01:
            narrow_count += 1

    score = narrow_count / lookback
    return max(0.0, min(1.0, score))
