"""
Factor: consecutive_up_days
Description: Count of consecutive up days (close > prev close)
Category: candlestick
"""

FACTOR_NAME = "consecutive_up_days"
FACTOR_DESC = "Count of consecutive up days — sustained buying pressure"
FACTOR_CATEGORY = "candlestick"


def compute(closes, highs, lows, volumes, idx):
    """Count consecutive up days. More = stronger momentum."""
    if idx < 1:
        return 0.5

    consecutive = 0
    for i in range(idx, 0, -1):
        if closes[i] > closes[i - 1]:
            consecutive += 1
        else:
            break

    # 0 = 0.4, 1 = 0.5, 2 = 0.6, 3 = 0.7, 5+ = 0.85, 7+ = 0.9
    if consecutive == 0:
        score = 0.4
    elif consecutive <= 2:
        score = 0.5 + consecutive * 0.05
    elif consecutive <= 5:
        score = 0.6 + (consecutive - 2) * 0.083
    else:
        score = 0.9

    return max(0.0, min(1.0, score))
