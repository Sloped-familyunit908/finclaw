"""Qlib Alpha158 RANK: Rolling price percentile — where current close sits among past N days."""
FACTOR_NAME = "qlib_rank_20d"
FACTOR_DESC = "Percentile rank of current close price among past 20 days' closes"
FACTOR_CATEGORY = "qlib_alpha158"

WINDOW = 20


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. 1.0 = highest in window, 0.0 = lowest in window."""
    if idx < WINDOW - 1:
        return 0.5

    current = closes[idx]
    count_below = 0

    for i in range(idx - WINDOW + 1, idx + 1):
        if closes[i] < current:
            count_below += 1

    score = count_below / float(WINDOW)  # already in [0, 1)
    return max(0.0, min(1.0, score))
