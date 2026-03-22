"""
Auto-generated factor: oversold_bounce_setup
Description: RSI<20 AND price at support AND volume declining (setup for bounce)
Category: mean_reversion
Generated: seed
"""

FACTOR_NAME = "oversold_bounce_setup"
FACTOR_DESC = "RSI<20 AND price at support AND volume declining (setup for bounce)"
FACTOR_CATEGORY = "mean_reversion"


def compute(closes, highs, lows, volumes, idx):
    """Multi-condition oversold bounce setup."""

    rsi_period = 14
    lookback = 30
    if idx < lookback + rsi_period:
        return 0.5

    # Compute RSI
    gains = 0.0
    losses = 0.0
    for j in range(idx - rsi_period + 1, idx + 1):
        change = closes[j] - closes[j - 1]
        if change > 0:
            gains += change
        else:
            losses -= change
    avg_gain = gains / rsi_period
    avg_loss = losses / rsi_period
    if avg_loss < 1e-10:
        rsi = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))

    # Check RSI < 20 (deeply oversold)
    rsi_oversold = rsi < 20.0

    # Check price near support (near 30-day low)
    min_low = lows[idx]
    for i in range(idx - lookback, idx):
        if lows[i] < min_low:
            min_low = lows[i]
    near_support = min_low > 0 and closes[idx] <= min_low * 1.03

    # Check volume declining (last 5 days trend down)
    vol_declining = True
    for i in range(idx - 3, idx + 1):
        if volumes[i] > volumes[i - 1]:
            vol_declining = False
            break

    score = 0.5
    conditions_met = 0
    if rsi_oversold:
        conditions_met += 1
        score += 0.15
    if near_support:
        conditions_met += 1
        score += 0.1
    if vol_declining:
        conditions_met += 1
        score += 0.1

    if conditions_met == 3:
        score = 0.95  # All conditions = very bullish setup

    return max(0.0, min(1.0, score))
