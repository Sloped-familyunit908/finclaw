"""
Factor: crypto_dynamic_rsi_period
Description: RSI with period scaled by volatility
Category: crypto
"""

FACTOR_NAME = "crypto_dynamic_rsi_period"
FACTOR_DESC = "RSI with period scaled by volatility"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. RSI with dynamically adjusted period."""
    base_period = 14
    vol_window = 24
    if idx < vol_window + base_period:
        return 0.5

    # Calculate volatility to adjust period
    returns = []
    for i in range(idx - vol_window, idx):
        if i < 1 or closes[i - 1] <= 0:
            continue
        returns.append(abs((closes[i] - closes[i - 1]) / closes[i - 1]))

    avg_vol = sum(returns) / len(returns) if returns else 0.01
    # High vol -> shorter RSI period
    period = max(5, min(28, int(base_period * 0.015 / max(avg_vol, 0.001))))

    if idx < period + 1:
        return 0.5

    gains = 0.0
    losses = 0.0
    for i in range(idx - period, idx):
        if i < 1:
            continue
        change = closes[i] - closes[i - 1]
        if change > 0:
            gains += change
        else:
            losses += abs(change)

    total = gains + losses
    if total <= 0:
        return 0.5

    rsi = gains / total
    return max(0.0, min(1.0, rsi))
