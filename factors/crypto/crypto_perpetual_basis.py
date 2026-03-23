"""
Factor: crypto_perpetual_basis
Description: (close - 24h_SMA) / 24h_SMA — contango/backwardation proxy
Category: crypto
"""

FACTOR_NAME = "crypto_perpetual_basis"
FACTOR_DESC = "Perpetual basis proxy — price deviation from 24h SMA as contango indicator"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = contango (premium), Low = backwardation (discount)."""
    lookback = 24
    if idx < lookback:
        return 0.5

    sma_24 = sum(closes[idx - lookback:idx]) / lookback
    if sma_24 <= 0:
        return 0.5

    basis = (closes[idx] - sma_24) / sma_24

    # Map: -2% → 0.0, 0% → 0.5, +2% → 1.0
    score = 0.5 + basis * 25.0
    return max(0.0, min(1.0, score))
