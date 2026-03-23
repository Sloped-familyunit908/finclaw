"""
Factor: crypto_bb_width_48
Description: Bollinger bandwidth 48-bar
Category: crypto
"""

FACTOR_NAME = "crypto_bb_width_48"
FACTOR_DESC = "Bollinger Band width over 48 bars"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Higher = wider bands (more volatile)."""
    period = 48
    if idx < period:
        return 0.5

    window = closes[idx - period + 1:idx + 1]
    mean = sum(window) / period
    if mean <= 0:
        return 0.5

    variance = sum((x - mean) ** 2 for x in window) / period
    std = variance ** 0.5

    bb_width = (4 * std) / mean

    # Typical BB width range: 2% to 20%
    score = bb_width / 0.20
    return max(0.0, min(1.0, score))
