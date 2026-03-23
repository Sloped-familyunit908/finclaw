"""
Factor: crypto_bb_width_24
Description: Bollinger bandwidth 24-bar
Category: crypto
"""

FACTOR_NAME = "crypto_bb_width_24"
FACTOR_DESC = "Bollinger Band width over 24 bars"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Higher = wider bands (more volatile)."""
    period = 24
    if idx < period:
        return 0.5

    window = closes[idx - period + 1:idx + 1]
    mean = sum(window) / period
    if mean <= 0:
        return 0.5

    variance = sum((x - mean) ** 2 for x in window) / period
    std = variance ** 0.5

    bb_width = (4 * std) / mean  # 2-sigma bands width as % of mean

    # Typical BB width range: 1% to 15%
    score = bb_width / 0.15
    return max(0.0, min(1.0, score))
