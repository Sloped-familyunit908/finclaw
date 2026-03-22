"""
Auto-generated factor: outside_day
Description: Today's range completely outside yesterday's range (expansion)
Category: pattern
Generated: seed
"""

FACTOR_NAME = "outside_day"
FACTOR_DESC = "Today's range completely outside yesterday's range (expansion)"
FACTOR_CATEGORY = "pattern"


def compute(closes, highs, lows, volumes, idx):
    """Detect outside day: today's range engulfs yesterday's range."""

    if idx < 2:
        return 0.5

    today_high = highs[idx]
    today_low = lows[idx]
    yest_high = highs[idx - 1]
    yest_low = lows[idx - 1]

    outside = today_high > yest_high and today_low < yest_low

    if outside:
        # Outside day = volatility expansion
        # Bullish if close near high, bearish if close near low
        day_range = today_high - today_low
        if day_range > 0:
            position = (closes[idx] - today_low) / day_range
            return max(0.0, min(1.0, position))
        return 0.5

    return 0.5
