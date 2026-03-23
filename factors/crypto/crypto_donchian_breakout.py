"""
Factor: crypto_donchian_breakout
Description: Price breaking above 24-bar Donchian high
Category: crypto
"""

FACTOR_NAME = "crypto_donchian_breakout"
FACTOR_DESC = "Price breaking above 24-bar Donchian high"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = breakout above channel, 0.5 = no breakout."""
    lookback = 24
    if idx < lookback + 1:
        return 0.5

    prev_upper = max(highs[idx - lookback - 1:idx - 1])
    if prev_upper <= 0:
        return 0.5

    price = closes[idx - 1]
    if price > prev_upper:
        overshoot = (price - prev_upper) / prev_upper
        score = 0.5 + min(overshoot * 20.0, 0.5)
    elif price < min(lows[idx - lookback - 1:idx - 1]):
        undershoot = (min(lows[idx - lookback - 1:idx - 1]) - price) / price if price > 0 else 0
        score = 0.5 - min(undershoot * 20.0, 0.5)
    else:
        score = 0.5

    return max(0.0, min(1.0, score))
