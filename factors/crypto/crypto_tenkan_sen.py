"""
Factor: crypto_tenkan_sen
Description: (highest_high_9 + lowest_low_9) / 2 — conversion line position
Category: crypto
"""

FACTOR_NAME = "crypto_tenkan_sen"
FACTOR_DESC = "(highest_high_9 + lowest_low_9) / 2 — conversion line position"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. >0.5 = price above tenkan, <0.5 = below."""
    period = 9
    if idx < period:
        return 0.5

    highest = max(highs[idx - period:idx])
    lowest = min(lows[idx - period:idx])
    tenkan = (highest + lowest) / 2.0

    if tenkan <= 0:
        return 0.5

    diff = (closes[idx - 1] - tenkan) / tenkan
    score = 0.5 + diff * 10.0
    return max(0.0, min(1.0, score))
