"""
Auto-generated factor: wide_range_bar
Description: Today's range is the widest of last 7 days
Category: pattern
Generated: seed
"""

FACTOR_NAME = "wide_range_bar"
FACTOR_DESC = "Today's range is the widest of last 7 days"
FACTOR_CATEGORY = "pattern"


def compute(closes, highs, lows, volumes, idx):
    """Detect wide range bar: today's range is widest of last 7 days."""

    lookback = 7
    if idx < lookback:
        return 0.5

    today_range = highs[idx] - lows[idx]
    is_widest = True

    for i in range(idx - lookback + 1, idx):
        day_range = highs[i] - lows[i]
        if day_range >= today_range:
            is_widest = False
            break

    if is_widest and today_range > 0:
        # Wide range bar - direction matters
        close_position = (closes[idx] - lows[idx]) / today_range
        # Close near high = bullish wide bar, close near low = bearish
        return max(0.0, min(1.0, close_position))

    return 0.5
