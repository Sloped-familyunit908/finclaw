"""
Factor: crypto_acceleration_score
Description: (roc_4h - roc_24h) normalized - accelerating vs decelerating
Category: crypto
"""

FACTOR_NAME = "crypto_acceleration_score"
FACTOR_DESC = "Momentum acceleration: short-term ROC vs long-term ROC"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Above 0.5 = accelerating."""
    if idx < 24:
        return 0.5

    if closes[idx - 4] <= 0 or closes[idx - 24] <= 0:
        return 0.5

    roc_4 = (closes[idx] - closes[idx - 4]) / closes[idx - 4]
    roc_24 = (closes[idx] - closes[idx - 24]) / closes[idx - 24]

    accel = roc_4 - roc_24
    score = 0.5 + (accel / 0.10)
    return max(0.0, min(1.0, score))
