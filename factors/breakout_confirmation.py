"""
Auto-generated factor: breakout_confirmation
Description: New high + above average volume + RSI not overbought
Category: composite
Generated: seed
"""

FACTOR_NAME = "breakout_confirmation"
FACTOR_DESC = "New high + above average volume + RSI not overbought"
FACTOR_CATEGORY = "composite"


def compute(closes, highs, lows, volumes, idx):
    """Confirmed breakout: new high + volume + RSI validation."""

    rsi_period = 14
    lookback = 20
    if idx < max(lookback, rsi_period) + 1:
        return 0.5

    # Check new 20-day high
    max_high = highs[idx - lookback]
    for i in range(idx - lookback, idx):
        if highs[i] > max_high:
            max_high = highs[i]
    new_high = highs[idx] > max_high

    # Volume check
    vol_total = 0.0
    for i in range(idx - lookback, idx):
        vol_total += volumes[i]
    avg_vol = vol_total / lookback
    above_avg_vol = volumes[idx] > avg_vol * 1.2

    # RSI check (not overbought)
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

    not_overbought = rsi < 70.0

    conditions = 0
    if new_high:
        conditions += 1
    if above_avg_vol:
        conditions += 1
    if not_overbought:
        conditions += 1

    if conditions == 3:
        return 0.95  # Full confirmation
    elif conditions == 2:
        return 0.75
    elif conditions == 1:
        return 0.6

    return 0.5
