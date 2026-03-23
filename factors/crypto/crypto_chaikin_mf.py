"""
Factor: crypto_chaikin_mf
Description: Chaikin Money Flow ((close-low)-(high-close))/(high-low)*volume
Category: crypto
"""

FACTOR_NAME = "crypto_chaikin_mf"
FACTOR_DESC = "Chaikin Money Flow indicator"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Above 0.5 = buying pressure, below = selling pressure."""
    period = 20
    if idx < period:
        return 0.5

    cmf_num = 0.0
    cmf_den = 0.0

    for i in range(idx - period + 1, idx + 1):
        hl_range = highs[i] - lows[i]
        if hl_range <= 0:
            continue
        clv = ((closes[i] - lows[i]) - (highs[i] - closes[i])) / hl_range
        cmf_num += clv * volumes[i]
        cmf_den += volumes[i]

    if cmf_den <= 0:
        return 0.5

    cmf = cmf_num / cmf_den  # Range: -1 to +1

    score = 0.5 + cmf * 0.5
    return max(0.0, min(1.0, score))
