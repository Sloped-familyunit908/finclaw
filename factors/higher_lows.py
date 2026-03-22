"""
Factor: higher_lows
Description: Count of days making higher lows in last 10 days (uptrend quality)
Category: momentum
"""

FACTOR_NAME = "higher_lows"
FACTOR_DESC = "Higher lows count — uptrend quality indicator over last 10 bars"
FACTOR_CATEGORY = "momentum"


def compute(closes, highs, lows, volumes, idx):
    """Count days where low > previous day's low. More = stronger uptrend."""
    period = 10
    if idx < period:
        return 0.5

    hl_count = 0
    for i in range(idx - period + 1, idx + 1):
        if lows[i] > lows[i - 1]:
            hl_count += 1

    # Normalize: 0/10 = 0.1, 5/10 = 0.5, 10/10 = 0.95
    score = 0.1 + (hl_count / float(period)) * 0.85

    return max(0.0, min(1.0, score))
