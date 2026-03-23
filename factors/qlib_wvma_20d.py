"""Qlib Alpha158 WVMA: Volume-weighted price change volatility."""
FACTOR_NAME = "qlib_wvma_20d"
FACTOR_DESC = "Std of |return|*volume / Mean of |return|*volume over 20 days"
FACTOR_CATEGORY = "qlib_alpha158"

WINDOW = 20


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Higher = more erratic volume-weighted price changes."""
    if idx < WINDOW:
        return 0.5

    weighted = []

    for i in range(idx - WINDOW + 1, idx + 1):
        if closes[i - 1] == 0:
            weighted.append(0.0)
            continue
        abs_ret = abs(closes[i] / closes[i - 1] - 1.0)
        w = abs_ret * volumes[i]
        weighted.append(w)

    n = len(weighted)
    mean_w = sum(weighted) / n

    if mean_w < 1e-12:
        return 0.5

    variance = sum((w - mean_w) ** 2 for w in weighted) / n
    std_w = variance ** 0.5

    ratio = std_w / mean_w  # coefficient of variation, typically [0, 3+]

    # Clip and normalize
    score = min(1.0, ratio / 3.0)
    return max(0.0, min(1.0, score))
