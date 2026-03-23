"""
Factor: crypto_max_drawdown_24h
Description: Maximum drawdown in last 24 bars
Category: crypto
"""

FACTOR_NAME = "crypto_max_drawdown_24h"
FACTOR_DESC = "Maximum drawdown over last 24 bars — worst peak-to-trough decline"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = small drawdown (healthy), Low = large drawdown."""
    lookback = 24
    if idx < lookback:
        return 0.5

    peak = closes[idx - lookback]
    max_dd = 0.0

    for i in range(idx - lookback, idx + 1):
        if closes[i] > peak:
            peak = closes[i]
        if peak > 0:
            dd = (peak - closes[i]) / peak
            if dd > max_dd:
                max_dd = dd

    # Map: 0% drawdown → 1.0, 5% → 0.5, 10%+ → 0.0
    score = 1.0 - max_dd * 10.0
    return max(0.0, min(1.0, score))
