"""
Factor: breadth_new_highs_lows
Description: Proximity to 20-day highs vs lows — breadth proxy
Category: market_breadth
"""

FACTOR_NAME = "breadth_new_highs_lows"
FACTOR_DESC = "Near 20-day highs vs lows — proxy for market breadth"
FACTOR_CATEGORY = "market_breadth"


def compute(closes, highs, lows, volumes, idx):
    """Measure if the stock is near 20-day highs or lows.
    This proxies market breadth for a single stock:
    near highs = broad strength, near lows = weakness.
    Score = position within the 20-day range.
    """
    period = 20
    if idx < period:
        return 0.5

    high_20d = max(highs[idx - period + 1 : idx + 1])
    low_20d = min(lows[idx - period + 1 : idx + 1])

    range_20d = high_20d - low_20d
    if range_20d <= 0:
        return 0.5

    # Position: 0 = at 20d low, 1 = at 20d high
    position = (closes[idx] - low_20d) / range_20d

    return max(0.0, min(1.0, position))
