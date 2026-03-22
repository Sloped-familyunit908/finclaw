"""
Factor: range_expansion
Description: Today's range vs 10-day average range
Category: volatility
"""

FACTOR_NAME = "range_expansion"
FACTOR_DESC = "Range expansion — today's range vs 10-day average"
FACTOR_CATEGORY = "volatility"


def compute(closes, highs, lows, volumes, idx):
    """Today's high-low range compared to recent average."""
    period = 10
    if idx < period:
        return 0.5

    today_range = highs[idx] - lows[idx]

    # 10-day average range
    total = 0.0
    for i in range(idx - period, idx):
        total += highs[i] - lows[i]
    avg_range = total / period

    if avg_range <= 0:
        return 0.5

    ratio = today_range / avg_range

    # Range expansion with bullish close = strong move
    bullish_close = closes[idx] > closes[idx - 1]

    if ratio > 2.0:
        # Major expansion
        score = 0.85 if bullish_close else 0.2
    elif ratio > 1.5:
        score = 0.7 if bullish_close else 0.3
    elif ratio > 1.0:
        score = 0.6 if bullish_close else 0.4
    elif ratio > 0.5:
        score = 0.5
    else:
        # Very narrow range = potential breakout
        score = 0.55

    return max(0.0, min(1.0, score))
