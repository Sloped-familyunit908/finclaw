"""
Auto-generated factor: price_oscillator
Description: (MA5 - MA20) / MA20 x 100 as percentage oscillator
Category: mean_reversion
Generated: seed
"""

FACTOR_NAME = "price_oscillator"
FACTOR_DESC = "(MA5 - MA20) / MA20 x 100 as percentage oscillator"
FACTOR_CATEGORY = "mean_reversion"


def compute(closes, highs, lows, volumes, idx):
    """Price oscillator: (MA5 - MA20) / MA20 * 100."""

    if idx < 20:
        return 0.5

    # MA5
    ma5_total = 0.0
    for i in range(idx - 4, idx + 1):
        ma5_total += closes[i]
    ma5 = ma5_total / 5.0

    # MA20
    ma20_total = 0.0
    for i in range(idx - 19, idx + 1):
        ma20_total += closes[i]
    ma20 = ma20_total / 20.0

    if ma20 < 1e-10:
        return 0.5

    osc = (ma5 - ma20) / ma20 * 100.0

    # Map oscillator from [-5%, +5%] to [0, 1]
    score = 0.5 + (osc / 10.0)
    return max(0.0, min(1.0, score))
