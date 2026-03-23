"""
Factor: crypto_close_location_value
Description: Where close sits in high-low range averaged over 24 bars
Category: crypto
"""

FACTOR_NAME = "crypto_close_location_value"
FACTOR_DESC = "Where close sits in high-low range averaged over 24 bars"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. 1.0 = always closing at highs, 0.0 = at lows."""
    lookback = 24
    if idx < lookback:
        return 0.5

    values = []
    for i in range(idx - lookback, idx):
        r = highs[i] - lows[i]
        if r <= 0:
            values.append(0.5)
            continue
        values.append((closes[i] - lows[i]) / r)

    return max(0.0, min(1.0, sum(values) / len(values)))
