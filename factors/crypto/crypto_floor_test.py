"""
Factor: crypto_floor_test
Description: Price testing recent support (within 0.5% of 48h low)
Category: crypto
"""

FACTOR_NAME = "crypto_floor_test"
FACTOR_DESC = "Price near 48h low — testing support/floor"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = price at support (could bounce or break)."""
    lookback = 48
    if idx < lookback:
        return 0.5

    low_48h = min(lows[idx - lookback:idx])
    if low_48h <= 0:
        return 0.5

    distance = (closes[idx] - low_48h) / low_48h

    # Within 0.5% of low = testing support
    if distance < 0.005:
        # Count how many times this level has been tested
        tests = 0
        for i in range(idx - lookback, idx):
            if lows[i] > 0 and (lows[i] - low_48h) / low_48h < 0.005:
                tests += 1
        # More tests = stronger support
        strength = min(tests / 5.0, 1.0)
        score = 0.5 + strength * 0.4
        return max(0.0, min(1.0, score))

    return 0.5
