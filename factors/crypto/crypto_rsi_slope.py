"""
Factor: crypto_rsi_slope
Description: Slope of RSI over last 6 bars (momentum of momentum)
Category: crypto
"""

FACTOR_NAME = "crypto_rsi_slope"
FACTOR_DESC = "Slope of RSI over last 6 bars"
FACTOR_CATEGORY = "crypto"


def _rsi_at(closes, period, end_idx):
    """Compute RSI at a specific index."""
    if end_idx < period + 1:
        return 50.0
    gains = 0.0
    losses = 0.0
    for i in range(end_idx - period, end_idx):
        change = closes[i + 1] - closes[i]
        if change > 0:
            gains += change
        else:
            losses += abs(change)
    if losses == 0:
        return 100.0
    if gains == 0:
        return 0.0
    rs = (gains / period) / (losses / period)
    return 100 - (100 / (1 + rs))


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Above 0.5 = RSI rising."""
    rsi_period = 14
    slope_bars = 6
    if idx < rsi_period + slope_bars + 1:
        return 0.5

    rsi_now = _rsi_at(closes, rsi_period, idx)
    rsi_prev = _rsi_at(closes, rsi_period, idx - slope_bars)

    slope = rsi_now - rsi_prev

    # Normalize: typical RSI slope range -30 to +30 over 6 bars
    score = 0.5 + (slope / 60.0)
    return max(0.0, min(1.0, score))
