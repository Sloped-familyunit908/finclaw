"""
Factor: ma5_distance
Description: Distance from 5-day MA as percentage, normalized
Category: moving_average
"""

FACTOR_NAME = "ma5_distance"
FACTOR_DESC = "Distance from 5-day MA as percentage, normalized"
FACTOR_CATEGORY = "moving_average"


def compute(closes, highs, lows, volumes, idx):
    """Percentage distance from MA5. Positive = above MA (bullish)."""
    period = 5
    if idx < period:
        return 0.5

    ma = sum(closes[idx - period + 1:idx + 1]) / period
    if ma <= 0:
        return 0.5

    pct_distance = (closes[idx] - ma) / ma  # e.g., 0.03 = 3% above

    # Normalize: -10% maps to 0.0, 0% maps to 0.5, +10% maps to 1.0
    score = 0.5 + pct_distance * 5.0

    return max(0.0, min(1.0, score))
