"""
Factor: crypto_accumulation_dist_line
Description: A/D line: ((C-L)-(H-C))/(H-L) * Vol cumulated
Category: crypto
"""

FACTOR_NAME = "crypto_accumulation_dist_line"
FACTOR_DESC = "A/D line: ((C-L)-(H-C))/(H-L) * Vol cumulated"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. >0.5 = accumulation, <0.5 = distribution."""
    lookback = 24
    if idx < lookback:
        return 0.5

    ad_sum = 0.0
    vol_sum = 0.0
    for i in range(idx - lookback, idx):
        r = highs[i] - lows[i]
        if r <= 0:
            continue
        clv = ((closes[i] - lows[i]) - (highs[i] - closes[i])) / r
        ad_sum += clv * volumes[i]
        vol_sum += volumes[i]

    if vol_sum <= 0:
        return 0.5

    normalized = ad_sum / vol_sum
    score = 0.5 + normalized * 0.5
    return max(0.0, min(1.0, score))
