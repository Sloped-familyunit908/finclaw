"""
Factor: crypto_kijun_sen
Description: (highest_high_26 + lowest_low_26) / 2 — base line position
Category: crypto
"""

FACTOR_NAME = "crypto_kijun_sen"
FACTOR_DESC = "(highest_high_26 + lowest_low_26) / 2 — base line position"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. >0.5 = price above kijun, <0.5 = below."""
    period = 26
    if idx < period:
        return 0.5

    highest = max(highs[idx - period:idx])
    lowest = min(lows[idx - period:idx])
    kijun = (highest + lowest) / 2.0

    if kijun <= 0:
        return 0.5

    diff = (closes[idx - 1] - kijun) / kijun
    score = 0.5 + diff * 10.0
    return max(0.0, min(1.0, score))
