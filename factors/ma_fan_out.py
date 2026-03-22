"""
Factor: ma_fan_out
Description: MA5 > MA10 > MA20 and they're spreading apart (bullish fan)
Category: moving_average
"""

FACTOR_NAME = "ma_fan_out"
FACTOR_DESC = "MA5 > MA10 > MA20 and they are spreading apart (bullish fan)"
FACTOR_CATEGORY = "moving_average"


def compute(closes, highs, lows, volumes, idx):
    """Bullish fan: MA5 > MA10 > MA20, spreads widening."""
    if idx < 21:
        return 0.5

    ma5 = sum(closes[idx - 4:idx + 1]) / 5
    ma10 = sum(closes[idx - 9:idx + 1]) / 10
    ma20 = sum(closes[idx - 19:idx + 1]) / 20

    if ma20 <= 0:
        return 0.5

    # Check ordering
    if ma5 > ma10 > ma20:
        # Measure spread as percentage
        spread_5_10 = (ma5 - ma10) / ma20
        spread_10_20 = (ma10 - ma20) / ma20
        total_spread = spread_5_10 + spread_10_20

        # Also check if spreading is increasing vs yesterday
        if idx >= 22:
            ma5_y = sum(closes[idx - 5:idx]) / 5
            ma10_y = sum(closes[idx - 10:idx]) / 10
            ma20_y = sum(closes[idx - 20:idx]) / 20
            if ma20_y > 0:
                spread_y = ((ma5_y - ma10_y) + (ma10_y - ma20_y)) / ma20_y
                widening = total_spread > spread_y
            else:
                widening = False
        else:
            widening = False

        base = 0.65 if widening else 0.6
        score = base + min(total_spread * 10, 0.35)
        return max(0.0, min(1.0, score))

    elif ma5 < ma10 < ma20:
        # Bearish fan
        return 0.2
    else:
        return 0.5
