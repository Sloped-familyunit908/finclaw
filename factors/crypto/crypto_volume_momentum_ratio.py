"""
Factor: crypto_volume_momentum_ratio
Description: Recent 6h volume vs previous 6h — volume momentum
Category: crypto
"""

FACTOR_NAME = "crypto_volume_momentum_ratio"
FACTOR_DESC = "Volume momentum — recent 6h volume divided by previous 6h volume"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = volume accelerating, Low = decelerating."""
    if idx < 24:
        return 0.5

    recent = sum(volumes[idx - 6:idx])
    earlier = sum(volumes[idx - 12:idx - 6])

    if earlier <= 0:
        return 0.5

    ratio = recent / earlier
    # ratio 1.0 = neutral, >1 = accelerating, <1 = decelerating
    # Map: 0.5x → 0.0, 1.0x → 0.5, 2.0x → 1.0
    score = ratio / 2.0
    return max(0.0, min(1.0, score))
