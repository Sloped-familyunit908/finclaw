"""
Factor: crypto_rubber_band
Description: Distance from 24h EMA multiplied by velocity — elastic snap-back indicator
Category: crypto
"""

FACTOR_NAME = "crypto_rubber_band"
FACTOR_DESC = "Rubber band effect — distance from EMA times velocity for snap-back potential"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = stretched above EMA (might snap back down), Low = below."""
    if idx < 48:
        return 0.5

    # Compute 24h EMA
    mult = 2.0 / 25.0
    ema = closes[idx - 48]
    for i in range(idx - 47, idx + 1):
        ema = closes[i] * mult + ema * (1.0 - mult)

    if ema <= 0:
        return 0.5

    # Distance from EMA as percentage
    distance = (closes[idx] - ema) / ema

    # Velocity: rate of price change over last 6 bars
    if closes[idx - 6] <= 0:
        return 0.5
    velocity = (closes[idx] - closes[idx - 6]) / closes[idx - 6]

    # Rubber band: distance * velocity (same direction amplifies)
    rubber = distance * abs(velocity) * 100.0

    # Map to 0-1: negative rubber = bearish stretched, positive = bullish stretched
    score = 0.5 + rubber
    return max(0.0, min(1.0, score))
