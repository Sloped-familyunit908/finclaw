"""
Auto-generated factor: narrow_range_7
Description: Today's range is the narrowest of last 7 days (NR7 pattern)
Category: pattern
Generated: seed
"""

FACTOR_NAME = "narrow_range_7"
FACTOR_DESC = "Today's range is the narrowest of last 7 days (NR7 pattern)"
FACTOR_CATEGORY = "pattern"


def compute(closes, highs, lows, volumes, idx):
    """Detect NR7: today's range is narrowest of last 7 days."""

    lookback = 7
    if idx < lookback:
        return 0.5

    today_range = highs[idx] - lows[idx]
    is_narrowest = True

    for i in range(idx - lookback + 1, idx):
        day_range = highs[i] - lows[i]
        if day_range <= today_range:
            is_narrowest = False
            break

    if is_narrowest:
        # NR7 = compression = breakout imminent
        # Slightly bullish bias (breakouts tend to resolve in trend direction)
        if idx >= 10:
            trend = (closes[idx] - closes[idx - 10]) / closes[idx - 10] if closes[idx - 10] > 0 else 0.0
            if trend > 0:
                return 0.7  # NR7 in uptrend
            else:
                return 0.55  # NR7 in downtrend
        return 0.65

    return 0.5
