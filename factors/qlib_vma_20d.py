"""Qlib Alpha158 VMA: Volume moving average ratio — current volume vs historical mean."""
FACTOR_NAME = "qlib_vma_20d"
FACTOR_DESC = "Volume moving average ratio: Mean(volume, 20) / current_volume"
FACTOR_CATEGORY = "qlib_alpha158"

WINDOW = 20


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. <0.5 = volume above average (active), >0.5 = below (quiet)."""
    if idx < WINDOW - 1:
        return 0.5

    total = 0.0
    for i in range(idx - WINDOW + 1, idx + 1):
        total += volumes[i]

    mean_vol = total / WINDOW
    current_vol = volumes[idx]

    if current_vol < 1e-12:
        return 0.5

    ratio = mean_vol / current_vol  # >1 = current below avg, <1 = current above avg

    # Qlib raw ratio can be wide; clip to [0.2, 5] then normalize
    ratio_clipped = max(0.2, min(5.0, ratio))
    # Log-scale normalization: log(0.2)=-1.6, log(5)=1.6
    import math
    log_ratio = math.log(ratio_clipped)
    score = 0.5 + log_ratio / 3.2  # maps [-1.6, 1.6] -> [0, 1]

    return max(0.0, min(1.0, score))
