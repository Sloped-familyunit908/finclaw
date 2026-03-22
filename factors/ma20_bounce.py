"""
Factor: ma20_bounce
Description: Price bouncing off 20-day MA from below
Category: moving_average
"""

FACTOR_NAME = "ma20_bounce"
FACTOR_DESC = "Price bouncing off 20-day MA from below"
FACTOR_CATEGORY = "moving_average"


def compute(closes, highs, lows, volumes, idx):
    """Close was below MA20 yesterday, close is above or touching MA20 today."""
    period = 20
    if idx < period + 1:
        return 0.5

    ma_today = sum(closes[idx - period + 1:idx + 1]) / period
    ma_yesterday = sum(closes[idx - period:idx]) / period

    yesterday_close = closes[idx - 1]
    today_close = closes[idx]

    if yesterday_close < ma_yesterday and today_close >= ma_today:
        if ma_today > 0:
            overshoot = (today_close - ma_today) / ma_today
            score = 0.6 + min(overshoot * 20, 0.4)
        else:
            score = 0.7
    elif today_close >= ma_today:
        score = 0.55
    else:
        distance = (ma_today - today_close) / ma_today if ma_today > 0 else 0
        score = 0.5 - min(distance * 10, 0.4)

    return max(0.0, min(1.0, score))
