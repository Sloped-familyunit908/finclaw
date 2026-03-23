"""
Factor: crypto_fractal_adaptive_ma
Description: MA weighted by fractal dimension estimate
Category: crypto
"""

FACTOR_NAME = "crypto_fractal_adaptive_ma"
FACTOR_DESC = "MA weighted by fractal dimension estimate"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. >0.5 = price above fractal-adaptive MA."""
    lookback = 24
    if idx < lookback + 1:
        return 0.5

    # Estimate fractal dimension via range scaling
    half = lookback // 2
    full_range = max(highs[idx - lookback:idx]) - min(lows[idx - lookback:idx])
    half1_range = max(highs[idx - lookback:idx - half]) - min(lows[idx - lookback:idx - half])
    half2_range = max(highs[idx - half:idx]) - min(lows[idx - half:idx])

    if full_range <= 0:
        return 0.5

    half_sum = half1_range + half2_range
    if half_sum <= 0:
        return 0.5

    # Fractal dimension proxy
    import math
    fdi = 1.0 + (math.log(half_sum / full_range) / math.log(2.0)) if half_sum > full_range * 0.01 else 1.5

    # Use fractal dimension to weight MA period
    alpha = max(0.01, min(1.0, 2.0 - fdi))

    # Adaptive MA
    ma = closes[idx - lookback]
    for i in range(idx - lookback + 1, idx):
        ma = alpha * closes[i] + (1 - alpha) * ma

    if ma <= 0:
        return 0.5

    diff = (closes[idx - 1] - ma) / ma
    score = 0.5 + diff * 15.0
    return max(0.0, min(1.0, score))
