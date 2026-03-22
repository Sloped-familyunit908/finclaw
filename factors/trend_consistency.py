"""
Factor: trend_consistency
Description: Percentage of last 20 days that were positive
Category: momentum
"""

FACTOR_NAME = "trend_consistency"
FACTOR_DESC = "Trend consistency — percentage of last 20 days with positive returns"
FACTOR_CATEGORY = "momentum"


def compute(closes, highs, lows, volumes, idx):
    """What fraction of last 20 days had close > prev close."""
    period = 20
    if idx < period:
        return 0.5

    up_count = 0
    for i in range(idx - period + 1, idx + 1):
        if closes[i] > closes[i - 1]:
            up_count += 1

    # Directly maps to [0, 1]: 0% up = 0.0, 50% = 0.5, 100% = 1.0
    score = up_count / float(period)

    return max(0.0, min(1.0, score))
