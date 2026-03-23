"""Qlib Alpha158 SUMD: Difference of positive and negative return sums, normalized."""
FACTOR_NAME = "qlib_sumd_20d"
FACTOR_DESC = "Net gain-loss ratio over 20 days: (sum_gains - sum_losses) / sum_abs_changes"
FACTOR_CATEGORY = "qlib_alpha158"

WINDOW = 20


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. >0.5 = net gains dominate, <0.5 = net losses dominate."""
    if idx < WINDOW:
        return 0.5

    sum_pos = 0.0
    sum_neg = 0.0
    sum_abs = 0.0

    for i in range(idx - WINDOW + 1, idx + 1):
        change = closes[i] - closes[i - 1]
        if change > 0:
            sum_pos += change
        elif change < 0:
            sum_neg += (-change)
        sum_abs += abs(change)

    if sum_abs < 1e-12:
        return 0.5

    sumd = (sum_pos - sum_neg) / sum_abs  # in [-1, 1]
    score = 0.5 + sumd * 0.5  # map to [0, 1]

    return max(0.0, min(1.0, score))
