"""
Auto-generated factor: inside_day
Description: Today's range completely within yesterday's range (consolidation)
Category: pattern
Generated: seed
"""

FACTOR_NAME = "inside_day"
FACTOR_DESC = "Today's range completely within yesterday's range (consolidation)"
FACTOR_CATEGORY = "pattern"


def compute(closes, highs, lows, volumes, idx):
    """Detect inside day: today's range within yesterday's range."""

    if idx < 2:
        return 0.5

    today_high = highs[idx]
    today_low = lows[idx]
    yest_high = highs[idx - 1]
    yest_low = lows[idx - 1]

    inside = today_high <= yest_high and today_low >= yest_low

    if inside:
        # Inside day = consolidation, slightly bullish (energy building)
        # Check trend context
        if idx >= 5:
            trend = (closes[idx] - closes[idx - 5]) / closes[idx - 5] if closes[idx - 5] > 0 else 0.0
            if trend > 0:
                return 0.65  # Inside day in uptrend = continuation
            else:
                return 0.55  # Inside day in downtrend = potential reversal
        return 0.6

    return 0.5
