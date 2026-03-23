"""
Factor: crypto_previous_day_low_test
Description: Testing yesterday's (24-bar ago) low level
Category: crypto
"""

FACTOR_NAME = "crypto_previous_day_low_test"
FACTOR_DESC = "Testing yesterday's (24-bar ago) low level"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = price testing previous day low."""
    lookback = 24
    if idx < lookback + 24:
        return 0.5

    prev_day_low = min(lows[idx - lookback * 2:idx - lookback])
    if prev_day_low <= 0:
        return 0.5

    distance = abs(closes[idx - 1] - prev_day_low) / prev_day_low

    score = max(0.0, 1.0 - distance * 50.0)
    return max(0.0, min(1.0, score))
