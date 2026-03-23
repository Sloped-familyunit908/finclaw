"""Qlib Alpha158 VSTD: Volume standard deviation ratio — volume volatility measure."""
FACTOR_NAME = "qlib_vstd_20d"
FACTOR_DESC = "Volume standard deviation over 20 days divided by current volume"
FACTOR_CATEGORY = "qlib_alpha158"

WINDOW = 20


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Higher = more volatile volume relative to current level."""
    if idx < WINDOW - 1:
        return 0.5

    vals = []
    for i in range(idx - WINDOW + 1, idx + 1):
        vals.append(float(volumes[i]))

    mean_v = sum(vals) / len(vals)
    variance = sum((v - mean_v) ** 2 for v in vals) / len(vals)
    std_v = variance ** 0.5

    current_vol = volumes[idx]
    if current_vol < 1e-12:
        return 0.5

    ratio = std_v / current_vol  # typically [0, 3+]

    # Clip and normalize: [0, 3] -> [0, 1]
    score = min(1.0, ratio / 3.0)
    return max(0.0, min(1.0, score))
