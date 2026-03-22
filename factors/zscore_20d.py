"""
Auto-generated factor: zscore_20d
Description: Z-score of price relative to 20-day mean/std (how many std devs from mean)
Category: mean_reversion
Generated: seed
"""

FACTOR_NAME = "zscore_20d"
FACTOR_DESC = "Z-score of price relative to 20-day mean/std (how many std devs from mean)"
FACTOR_CATEGORY = "mean_reversion"


def compute(closes, highs, lows, volumes, idx):
    """Z-score of current close vs 20-day mean, mapped to [0,1]."""

    lookback = 20
    if idx < lookback:
        return 0.5

    total = 0.0
    for i in range(idx - lookback + 1, idx + 1):
        total += closes[i]
    mean = total / lookback

    var_sum = 0.0
    for i in range(idx - lookback + 1, idx + 1):
        diff = closes[i] - mean
        var_sum += diff * diff
    std = (var_sum / lookback) ** 0.5

    if std < 1e-10:
        return 0.5

    zscore = (closes[idx] - mean) / std

    # Map z-score from [-3, 3] to [0, 1]
    # Negative z-score (below mean) = oversold = bullish for mean reversion
    # So we invert: low z-score -> high score
    score = 0.5 - (zscore / 6.0)
    return max(0.0, min(1.0, score))
