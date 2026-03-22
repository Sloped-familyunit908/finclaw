"""
Auto-generated factor: positive_days_ratio_30d
Description: Fraction of last 30 days that closed positive
Category: relative_strength
Generated: seed
"""

FACTOR_NAME = "positive_days_ratio_30d"
FACTOR_DESC = "Fraction of last 30 days that closed positive"
FACTOR_CATEGORY = "relative_strength"


def compute(closes, highs, lows, volumes, idx):
    """Fraction of last 30 days with positive close-to-close return."""

    lookback = 30
    if idx < lookback:
        return 0.5

    positive = 0
    for i in range(idx - lookback + 1, idx + 1):
        if closes[i] > closes[i - 1]:
            positive += 1

    ratio = positive / float(lookback)
    return max(0.0, min(1.0, ratio))
