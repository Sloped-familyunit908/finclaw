"""
Factor: crypto_recovery_ratio
Description: Current price / recent peak — recovery progress
Category: crypto
"""

FACTOR_NAME = "crypto_recovery_ratio"
FACTOR_DESC = "Recovery ratio — current price relative to recent 48h peak"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = near peak (fully recovered), Low = far from peak."""
    lookback = 48
    if idx < lookback:
        return 0.5

    peak = max(highs[idx - lookback:idx])
    if peak <= 0:
        return 0.5

    ratio = closes[idx] / peak
    # ratio of 1.0 = at peak, 0.9 = 10% below
    return max(0.0, min(1.0, ratio))
