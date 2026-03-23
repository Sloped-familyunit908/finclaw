"""
Factor: crypto_climax_volume
Description: Current volume > 4x 48h average — climax/extreme volume event
Category: crypto
"""

FACTOR_NAME = "crypto_climax_volume"
FACTOR_DESC = "Climax volume detection — current volume exceeds 4x the 48h average"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = extreme climax volume detected."""
    lookback = 48
    if idx < lookback:
        return 0.5

    avg_vol = sum(volumes[idx - lookback:idx]) / lookback
    if avg_vol <= 0:
        return 0.5

    ratio = volumes[idx] / avg_vol

    if ratio < 2.0:
        return 0.5

    # Scale from 2x (0.5) to 8x+ (1.0)
    score = 0.5 + (ratio - 2.0) / 12.0
    return max(0.0, min(1.0, score))
