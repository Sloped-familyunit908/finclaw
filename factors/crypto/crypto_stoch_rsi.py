"""
Factor: crypto_stoch_rsi
Description: Stochastic RSI (RSI of RSI)
Category: crypto
"""

FACTOR_NAME = "crypto_stoch_rsi"
FACTOR_DESC = "Stochastic RSI - RSI normalized to its own range"
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
    """Returns float in [0, 1]. Stoch RSI directly maps to 0-1."""
    rsi_period = 14
    stoch_period = 14
    if idx < rsi_period + stoch_period + 1:
        return 0.5

    # Compute RSI values over stoch_period
    rsi_values = []
    for i in range(idx - stoch_period + 1, idx + 1):
        rsi_values.append(_rsi_at(closes, rsi_period, i))

    rsi_min = min(rsi_values)
    rsi_max = max(rsi_values)

    if rsi_max == rsi_min:
        return 0.5

    stoch_rsi = (rsi_values[-1] - rsi_min) / (rsi_max - rsi_min)
    return max(0.0, min(1.0, stoch_rsi))
