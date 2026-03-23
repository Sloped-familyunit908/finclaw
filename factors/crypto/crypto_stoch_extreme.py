"""
Factor: crypto_stoch_extreme
Description: %K < 20 (oversold) or > 80 (overbought)
Category: crypto
"""

FACTOR_NAME = "crypto_stoch_extreme"
FACTOR_DESC = "%K < 20 (oversold) or > 80 (overbought)"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Near 0 = overbought, near 1 = oversold, 0.5 = neutral."""
    lookback = 14
    if idx < lookback:
        return 0.5

    highest = max(highs[idx - lookback:idx])
    lowest = min(lows[idx - lookback:idx])
    r = highest - lowest
    if r <= 0:
        return 0.5

    k = (closes[idx - 1] - lowest) / r
    # Map: k>0.8 -> overbought (score near 0), k<0.2 -> oversold (score near 1)
    if k > 0.8:
        score = (1.0 - k) / 0.2 * 0.3
    elif k < 0.2:
        score = 1.0 - k / 0.2 * 0.3
    else:
        score = 0.5

    return max(0.0, min(1.0, score))
