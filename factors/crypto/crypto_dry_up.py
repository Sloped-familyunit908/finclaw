"""
Factor: crypto_dry_up
Description: Volume < 0.3x 48h average — low liquidity period
Category: crypto
"""

FACTOR_NAME = "crypto_dry_up"
FACTOR_DESC = "Volume dry-up detection — volume below 0.3x the 48h average"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = very low volume (liquidity dry-up)."""
    lookback = 48
    if idx < lookback:
        return 0.5

    avg_vol = sum(volumes[idx - lookback:idx]) / lookback
    if avg_vol <= 0:
        return 0.5

    ratio = volumes[idx] / avg_vol

    if ratio > 0.5:
        return 0.5

    # Scale: 0.5x → 0.5, 0.0x → 1.0 (extreme dry-up)
    score = 0.5 + (0.5 - ratio)
    return max(0.0, min(1.0, score))
