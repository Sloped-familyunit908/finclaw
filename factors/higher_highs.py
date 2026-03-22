"""
Factor: higher_highs
Description: Count of days making higher highs in last 10 days
Category: momentum
"""

FACTOR_NAME = "higher_highs"
FACTOR_DESC = "Higher highs count — how many days made new highs in last 10 bars"
FACTOR_CATEGORY = "momentum"


def compute(closes, highs, lows, volumes, idx):
    """Count days where high > previous day's high."""
    period = 10
    if idx < period:
        return 0.5

    hh_count = 0
    for i in range(idx - period + 1, idx + 1):
        if highs[i] > highs[i - 1]:
            hh_count += 1

    # Normalize: 0/10 = 0.1, 5/10 = 0.5, 10/10 = 0.95
    score = 0.1 + (hh_count / float(period)) * 0.85

    return max(0.0, min(1.0, score))
