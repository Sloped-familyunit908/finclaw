"""
Factor: crypto_mean_reversion_24h
Description: Distance from 24h VWAP — extreme deviations tend to revert
Category: crypto
"""

FACTOR_NAME = "crypto_mean_reversion_24h"
FACTOR_DESC = "24h VWAP mean reversion — extreme deviations from VWAP tend to revert in crypto"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """
    Computes distance from 24h VWAP (volume-weighted average price).
    Far below VWAP → expect reversion up → bullish
    Far above VWAP → expect reversion down → bearish
    Near VWAP → neutral
    """
    lookback = 24
    if idx < lookback:
        return 0.5

    # Calculate VWAP over 24h
    total_pv = 0.0  # price * volume
    total_vol = 0.0

    for i in range(idx - lookback + 1, idx + 1):
        typical_price = (highs[i] + lows[i] + closes[i]) / 3.0
        total_pv += typical_price * volumes[i]
        total_vol += volumes[i]

    if total_vol <= 0:
        return 0.5

    vwap = total_pv / total_vol

    if vwap <= 0:
        return 0.5

    # Distance from VWAP as percentage
    deviation_pct = (closes[idx] - vwap) / vwap

    # Mean reversion: below VWAP = bullish, above = bearish
    # -3% → 1.0 (very bullish), 0% → 0.5, +3% → 0.0 (very bearish)
    score = 0.5 - deviation_pct * (0.5 / 0.03)
    return max(0.0, min(1.0, score))
