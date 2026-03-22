"""
Factor: ma5_10_cross
Description: MA5 crossing above MA10 (golden cross = bullish)
Category: moving_average
"""

FACTOR_NAME = "ma5_10_cross"
FACTOR_DESC = "MA5 crossing above MA10 (golden cross = bullish)"
FACTOR_CATEGORY = "moving_average"


def compute(closes, highs, lows, volumes, idx):
    """Detect MA5 crossing above MA10. Recent cross = high score."""
    if idx < 11:
        return 0.5

    # Today's MAs
    ma5_today = sum(closes[idx - 4:idx + 1]) / 5
    ma10_today = sum(closes[idx - 9:idx + 1]) / 10

    # Yesterday's MAs
    ma5_yesterday = sum(closes[idx - 5:idx]) / 5
    ma10_yesterday = sum(closes[idx - 10:idx]) / 10

    # Fresh golden cross today
    if ma5_yesterday <= ma10_yesterday and ma5_today > ma10_today:
        return 0.9

    # MA5 above MA10 (bullish alignment)
    if ma5_today > ma10_today:
        spread = (ma5_today - ma10_today) / ma10_today if ma10_today > 0 else 0
        score = 0.55 + min(spread * 20, 0.3)
        return max(0.0, min(1.0, score))

    # Fresh death cross today
    if ma5_yesterday >= ma10_yesterday and ma5_today < ma10_today:
        return 0.1

    # MA5 below MA10 (bearish alignment)
    spread = (ma10_today - ma5_today) / ma10_today if ma10_today > 0 else 0
    score = 0.45 - min(spread * 20, 0.3)
    return max(0.0, min(1.0, score))
