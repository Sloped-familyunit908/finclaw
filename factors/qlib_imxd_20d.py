"""Qlib Alpha158 IMXD: Distance between index of max and index of min in rolling window."""
FACTOR_NAME = "qlib_imxd_20d"
FACTOR_DESC = "Normalized distance between max-high and min-low day indices over 20 days"
FACTOR_CATEGORY = "qlib_alpha158"

WINDOW = 20


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. >0.5 = max came after min (uptrend), <0.5 = max before min (downtrend)."""
    if idx < WINDOW - 1:
        return 0.5

    start = idx - WINDOW + 1

    max_high = highs[start]
    max_idx = 0
    min_low = lows[start]
    min_idx = 0

    for i in range(1, WINDOW):
        if highs[start + i] > max_high:
            max_high = highs[start + i]
            max_idx = i
        if lows[start + i] < min_low:
            min_low = lows[start + i]
            min_idx = i

    # Qlib formula: (IdxMax - IdxMin) / window
    imxd = (max_idx - min_idx) / float(WINDOW)  # in [-1, 1) approximately

    # Normalize to [0, 1]
    score = 0.5 + imxd * 0.5

    return max(0.0, min(1.0, score))
