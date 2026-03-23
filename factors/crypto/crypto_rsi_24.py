"""
Factor: crypto_rsi_24
Description: Slow RSI (24 periods)
Category: crypto
"""

FACTOR_NAME = "crypto_rsi_24"
FACTOR_DESC = "Slow RSI over 24 periods"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Maps RSI 0-100 to 0.0-1.0."""
    period = 24
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
        return 1.0
    if gains == 0:
        return 0.0

    rs = (gains / period) / (losses / period)
    rsi = 100 - (100 / (1 + rs))

    return max(0.0, min(1.0, rsi / 100.0))
