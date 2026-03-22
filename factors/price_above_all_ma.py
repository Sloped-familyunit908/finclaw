"""
Factor: price_above_all_ma
Description: Price above MA5, MA10, and MA20 simultaneously
Category: moving_average
"""

FACTOR_NAME = "price_above_all_ma"
FACTOR_DESC = "Price above MA5, MA10, and MA20 simultaneously"
FACTOR_CATEGORY = "moving_average"


def compute(closes, highs, lows, volumes, idx):
    """Count how many MAs price is above. All 3 = very bullish."""
    if idx < 20:
        return 0.5

    price = closes[idx]
    ma5 = sum(closes[idx - 4:idx + 1]) / 5
    ma10 = sum(closes[idx - 9:idx + 1]) / 10
    ma20 = sum(closes[idx - 19:idx + 1]) / 20

    above_count = 0
    if price >= ma5:
        above_count += 1
    if price >= ma10:
        above_count += 1
    if price >= ma20:
        above_count += 1

    # 0 above = 0.15, 1 = 0.35, 2 = 0.65, 3 = 0.85
    score = 0.15 + above_count * 0.233

    return max(0.0, min(1.0, score))
