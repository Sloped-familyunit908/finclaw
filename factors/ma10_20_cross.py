"""
Factor: ma10_20_cross
Description: MA10 crossing above MA20
Category: moving_average
"""

FACTOR_NAME = "ma10_20_cross"
FACTOR_DESC = "MA10 crossing above MA20"
FACTOR_CATEGORY = "moving_average"


def compute(closes, highs, lows, volumes, idx):
    """Detect MA10 crossing above MA20."""
    if idx < 21:
        return 0.5

    ma10_today = sum(closes[idx - 9:idx + 1]) / 10
    ma20_today = sum(closes[idx - 19:idx + 1]) / 20

    ma10_yesterday = sum(closes[idx - 10:idx]) / 10
    ma20_yesterday = sum(closes[idx - 20:idx]) / 20

    # Fresh golden cross
    if ma10_yesterday <= ma20_yesterday and ma10_today > ma20_today:
        return 0.9

    # MA10 above MA20
    if ma10_today > ma20_today:
        spread = (ma10_today - ma20_today) / ma20_today if ma20_today > 0 else 0
        score = 0.55 + min(spread * 15, 0.3)
        return max(0.0, min(1.0, score))

    # Fresh death cross
    if ma10_yesterday >= ma20_yesterday and ma10_today < ma20_today:
        return 0.1

    # MA10 below MA20
    spread = (ma20_today - ma10_today) / ma20_today if ma20_today > 0 else 0
    score = 0.45 - min(spread * 15, 0.3)
    return max(0.0, min(1.0, score))
