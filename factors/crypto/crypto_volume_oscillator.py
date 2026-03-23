"""
Factor: crypto_volume_oscillator
Description: Short EMA of volume / Long EMA of volume
Category: crypto
"""

FACTOR_NAME = "crypto_volume_oscillator"
FACTOR_DESC = "Volume oscillator — ratio of short-term to long-term volume EMA"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = short-term volume above long-term (expansion)."""
    if idx < 48:
        return 0.5

    # Compute short EMA (6-period) and long EMA (24-period) of volume
    short_period = 6
    long_period = 24
    short_mult = 2.0 / (short_period + 1)
    long_mult = 2.0 / (long_period + 1)

    short_ema = volumes[idx - 48]
    long_ema = volumes[idx - 48]

    for i in range(idx - 47, idx + 1):
        short_ema = volumes[i] * short_mult + short_ema * (1.0 - short_mult)
        long_ema = volumes[i] * long_mult + long_ema * (1.0 - long_mult)

    if long_ema <= 0:
        return 0.5

    ratio = short_ema / long_ema
    # Map: 0.5x → 0.0, 1.0x → 0.5, 2.0x → 1.0
    score = ratio / 2.0
    return max(0.0, min(1.0, score))
