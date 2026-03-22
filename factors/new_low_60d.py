"""
Auto-generated factor: new_low_60d
Description: Is price at 60-day low? (deeply oversold)
Category: relative_strength
Generated: seed
"""

FACTOR_NAME = "new_low_60d"
FACTOR_DESC = "Is price at 60-day low? (deeply oversold)"
FACTOR_CATEGORY = "relative_strength"


def compute(closes, highs, lows, volumes, idx):
    """Check if current price is at or near 60-day low (oversold = potential bounce)."""

    lookback = 60
    if idx < lookback:
        return 0.5

    # Find 60-day low
    min_low = lows[idx - lookback]
    for i in range(idx - lookback, idx + 1):
        if lows[i] < min_low:
            min_low = lows[i]

    if min_low < 1e-10:
        return 0.5

    # How close to 60-day low
    proximity = closes[idx] / min_low

    if proximity <= 1.01:
        return 0.1  # At new low - very bearish
    elif proximity <= 1.05:
        return 0.25  # Near low
    elif proximity <= 1.10:
        return 0.4
    elif proximity <= 1.20:
        return 0.5
    else:
        return 0.6  # Well above low
