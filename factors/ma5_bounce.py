"""
Factor: ma5_bounce
Description: Price bouncing off 5-day MA from below
Category: moving_average
"""

FACTOR_NAME = "ma5_bounce"
FACTOR_DESC = "Price bouncing off 5-day MA from below"
FACTOR_CATEGORY = "moving_average"


def compute(closes, highs, lows, volumes, idx):
    """Close was below MA5 yesterday, close is above or touching MA5 today."""
    period = 5
    if idx < period + 1:
        return 0.5

    # Today's MA5
    ma5_today = sum(closes[idx - period + 1:idx + 1]) / period
    # Yesterday's MA5
    ma5_yesterday = sum(closes[idx - period:idx]) / period

    yesterday_close = closes[idx - 1]
    today_close = closes[idx]

    # Yesterday below MA5, today above or at MA5
    if yesterday_close < ma5_yesterday and today_close >= ma5_today:
        # Strength based on how much it crossed above
        if ma5_today > 0:
            overshoot = (today_close - ma5_today) / ma5_today
            score = 0.6 + min(overshoot * 20, 0.4)
        else:
            score = 0.7
    elif today_close >= ma5_today:
        score = 0.55
    else:
        # Below MA5
        distance = (ma5_today - today_close) / ma5_today if ma5_today > 0 else 0
        score = 0.5 - min(distance * 10, 0.4)

    return max(0.0, min(1.0, score))
