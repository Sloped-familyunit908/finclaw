"""
Factor: crypto_win_streak
Description: Length of current winning streak (consecutive positive bars)
Category: crypto
"""

FACTOR_NAME = "crypto_win_streak"
FACTOR_DESC = "Length of current winning streak (consecutive positive bars)"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = long winning streak."""
    if idx < 2:
        return 0.5

    streak = 0
    for i in range(idx - 1, 0, -1):
        if closes[i] > closes[i - 1]:
            streak += 1
        else:
            break

    score = min(streak / 12.0, 1.0)
    return max(0.0, min(1.0, score))
