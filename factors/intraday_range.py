"""
Factor: intraday_range
Description: Average (high-low)/close over last 5 days
Category: volatility
"""

FACTOR_NAME = "intraday_range"
FACTOR_DESC = "Average intraday range relative to close over last 5 days"
FACTOR_CATEGORY = "volatility"


def compute(closes, highs, lows, volumes, idx):
    """Average (high - low) / close over last 5 days."""
    period = 5
    if idx < period:
        return 0.5

    total_range = 0.0
    valid = 0

    for i in range(idx - period + 1, idx + 1):
        if closes[i] > 0:
            day_range = (highs[i] - lows[i]) / closes[i]
            total_range += day_range
            valid += 1

    if valid == 0:
        return 0.5

    avg_range = total_range / valid

    # Low range (< 1%) = quiet, potential breakout
    # Normal (2-4%) = typical
    # High (> 5%) = volatile
    if avg_range < 0.01:
        score = 0.7  # Very quiet, breakout potential
    elif avg_range < 0.025:
        score = 0.55
    elif avg_range < 0.04:
        score = 0.5
    elif avg_range < 0.06:
        score = 0.4
    else:
        score = 0.3  # Very volatile

    return max(0.0, min(1.0, score))
