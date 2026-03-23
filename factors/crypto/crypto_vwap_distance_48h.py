"""
Factor: crypto_vwap_distance_48h
Description: Distance from 48-bar VWAP
Category: crypto
"""

FACTOR_NAME = "crypto_vwap_distance_48h"
FACTOR_DESC = "Distance from 48-bar VWAP"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. >0.5 = price above VWAP, <0.5 = below."""
    lookback = 48
    if idx < lookback:
        return 0.5

    cum_vol = 0.0
    cum_pv = 0.0
    for i in range(idx - lookback, idx):
        typical = (highs[i] + lows[i] + closes[i]) / 3.0
        cum_pv += typical * volumes[i]
        cum_vol += volumes[i]

    if cum_vol <= 0:
        return 0.5

    vwap = cum_pv / cum_vol
    if vwap <= 0:
        return 0.5

    diff = (closes[idx - 1] - vwap) / vwap
    score = 0.5 + diff * 10.0
    return max(0.0, min(1.0, score))
