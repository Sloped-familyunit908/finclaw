"""
Factor: crypto_trend_age
Description: How many bars since last trend change (EMA cross)
Category: crypto
"""

FACTOR_NAME = "crypto_trend_age"
FACTOR_DESC = "Age of current trend measured by bars since last EMA(8)/EMA(24) cross"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = mature trend (long-running)."""
    if idx < 48:
        return 0.5

    # Compute EMA(8) and EMA(24) series
    short_mult = 2.0 / 9.0
    long_mult = 2.0 / 25.0
    short_ema = closes[0]
    long_ema = closes[0]

    last_cross = 0
    prev_diff = 0

    for i in range(1, idx + 1):
        short_ema = closes[i] * short_mult + short_ema * (1.0 - short_mult)
        long_ema = closes[i] * long_mult + long_ema * (1.0 - long_mult)
        diff = short_ema - long_ema

        if prev_diff != 0:
            # Detect cross: sign change
            if (diff > 0 and prev_diff < 0) or (diff < 0 and prev_diff > 0):
                last_cross = i
        prev_diff = diff

    bars_since = idx - last_cross
    # Normalize: 0 bars → 0.0, 48+ bars → 1.0
    score = min(bars_since / 48.0, 1.0)
    return max(0.0, min(1.0, score))
