"""Qlib Alpha158 SUMP: Sum of positive returns ratio (RSI-like gain component)."""
FACTOR_NAME = "qlib_sump_20d"
FACTOR_DESC = "Sum of positive returns / sum of absolute returns over 20 days (RSI-like)"
FACTOR_CATEGORY = "qlib_alpha158"

WINDOW = 20


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Higher = more gains than losses over window."""
    if idx < WINDOW:
        return 0.5

    sum_pos = 0.0
    sum_abs = 0.0

    for i in range(idx - WINDOW + 1, idx + 1):
        change = closes[i] - closes[i - 1]
        if change > 0:
            sum_pos += change
        sum_abs += abs(change)

    if sum_abs < 1e-12:
        return 0.5

    score = sum_pos / sum_abs  # already in [0, 1]
    return max(0.0, min(1.0, score))
