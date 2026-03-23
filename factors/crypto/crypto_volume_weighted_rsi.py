"""
Factor: crypto_volume_weighted_rsi
Description: RSI weighted by volume in each period
Category: crypto
"""

FACTOR_NAME = "crypto_volume_weighted_rsi"
FACTOR_DESC = "RSI weighted by volume in each period"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Volume-weighted RSI normalized to [0,1]."""
    lookback = 14
    if idx < lookback + 1:
        return 0.5

    vol_gain = 0.0
    vol_loss = 0.0
    for i in range(idx - lookback, idx):
        if i < 1:
            continue
        change = closes[i] - closes[i - 1]
        if change > 0:
            vol_gain += change * volumes[i]
        else:
            vol_loss += abs(change) * volumes[i]

    if vol_gain + vol_loss <= 0:
        return 0.5

    vw_rsi = vol_gain / (vol_gain + vol_loss)
    return max(0.0, min(1.0, vw_rsi))
