"""
Factor: crypto_resistance_distance
Description: Distance to nearest 48h high
Category: crypto
"""

FACTOR_NAME = "crypto_resistance_distance"
FACTOR_DESC = "Price distance from 48-bar high (resistance)"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Near 0 = very close to resistance, near 1 = far from resistance."""
    lookback = 48
    if idx < lookback:
        return 0.5

    period_low = min(lows[idx - lookback:idx + 1])
    period_high = max(highs[idx - lookback:idx + 1])

    if period_high <= period_low:
        return 0.5

    price = closes[idx]
    distance = (period_high - price) / (period_high - period_low)
    return max(0.0, min(1.0, distance))
