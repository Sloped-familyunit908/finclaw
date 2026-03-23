"""
Factor: crypto_rsi_mean_reversion
Description: How far RSI is from 50 (extreme = reversal likely)
Category: crypto
"""

FACTOR_NAME = "crypto_rsi_mean_reversion"
FACTOR_DESC = "RSI distance from 50 - extreme values suggest reversal"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Higher = RSI more extreme (reversal likely)."""
    period = 14
    if idx < period + 1:
        return 0.5

    gains = 0.0
    losses = 0.0
    for i in range(idx - period, idx):
        change = closes[i + 1] - closes[i]
        if change > 0:
            gains += change
        else:
            losses += abs(change)

    if losses == 0:
        rsi = 100.0
    elif gains == 0:
        rsi = 0.0
    else:
        rs = (gains / period) / (losses / period)
        rsi = 100 - (100 / (1 + rs))

    # Distance from 50 normalized to [0, 1]
    distance = abs(rsi - 50) / 50.0
    return max(0.0, min(1.0, distance))
