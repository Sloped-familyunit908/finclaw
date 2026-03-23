"""
Factor: crypto_positive_volume_index
Description: Track price changes only on up-volume days
Category: crypto
"""

FACTOR_NAME = "crypto_positive_volume_index"
FACTOR_DESC = "Positive Volume Index - price changes on up-volume bars"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Above 0.5 = up-volume bars have positive returns."""
    lookback = 24
    if idx < lookback + 1:
        return 0.5

    avg_vol = sum(volumes[idx - lookback:idx]) / lookback
    if avg_vol <= 0:
        return 0.5

    pvi_return = 0.0
    pvi_count = 0

    for i in range(idx - lookback + 1, idx + 1):
        if volumes[i] > volumes[i - 1] and closes[i - 1] > 0:
            pvi_return += (closes[i] - closes[i - 1]) / closes[i - 1]
            pvi_count += 1

    if pvi_count == 0:
        return 0.5

    avg_pvi_return = pvi_return / pvi_count

    # Normalize: typical range -2% to +2%
    score = 0.5 + (avg_pvi_return / 0.04)
    return max(0.0, min(1.0, score))
