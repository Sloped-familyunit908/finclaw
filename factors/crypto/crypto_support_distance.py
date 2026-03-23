"""
Factor: crypto_support_distance
Description: Distance to nearest 48h low
Category: crypto
"""

FACTOR_NAME = "crypto_support_distance"
FACTOR_DESC = "Price distance from 48-bar low (support)"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Near 0 = very close to support, near 1 = far from support."""
    lookback = 48
    if idx < lookback:
        return 0.5

    period_low = min(lows[idx - lookback:idx + 1])
    period_high = max(highs[idx - lookback:idx + 1])

    if period_high <= period_low:
        return 0.5

    price = closes[idx]
    distance = (price - period_low) / (period_high - period_low)
    return max(0.0, min(1.0, distance))
