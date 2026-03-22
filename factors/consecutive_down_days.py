"""
Factor: consecutive_down_days
Description: Count of consecutive down days (bearish exhaustion when many)
Category: candlestick
"""

FACTOR_NAME = "consecutive_down_days"
FACTOR_DESC = "Consecutive down days — more days = higher exhaustion/reversal probability"
FACTOR_CATEGORY = "candlestick"


def compute(closes, highs, lows, volumes, idx):
    """Count consecutive down days. Many = bearish exhaustion = potential bounce."""
    if idx < 1:
        return 0.5

    consecutive = 0
    for i in range(idx, 0, -1):
        if closes[i] < closes[i - 1]:
            consecutive += 1
        else:
            break

    # More down days = higher score (more likely to reverse)
    # 0 = 0.5, 1 = 0.45, 2 = 0.5, 3 = 0.55, 5+ = 0.7, 7+ = 0.85
    if consecutive == 0:
        score = 0.5
    elif consecutive == 1:
        score = 0.45
    elif consecutive == 2:
        score = 0.5
    elif consecutive <= 4:
        score = 0.55 + (consecutive - 3) * 0.075
    elif consecutive <= 6:
        score = 0.7 + (consecutive - 5) * 0.05
    else:
        score = 0.85

    return max(0.0, min(1.0, score))
