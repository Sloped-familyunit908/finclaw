"""
Auto-generated factor: capitulation_signal
Description: Extreme volume + extreme price drop + RSI<10 (panic selling exhaustion)
Category: composite
Generated: seed
"""

FACTOR_NAME = "capitulation_signal"
FACTOR_DESC = "Extreme volume + extreme price drop + RSI<10 (panic selling exhaustion)"
FACTOR_CATEGORY = "composite"


def compute(closes, highs, lows, volumes, idx):
    """Capitulation signal: extreme selling exhaustion."""

    rsi_period = 14
    lookback = 20
    if idx < max(lookback, rsi_period) + 1:
        return 0.5

    # Daily return
    daily_return = (closes[idx] - closes[idx - 1]) / closes[idx - 1] if closes[idx - 1] > 0 else 0.0

    # Volume spike
    vol_total = 0.0
    for i in range(idx - lookback, idx):
        vol_total += volumes[i]
    avg_vol = vol_total / lookback
    vol_ratio = volumes[idx] / avg_vol if avg_vol > 0 else 1.0

    # RSI
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

    # Capitulation: extreme drop + extreme volume + extremely oversold RSI
    extreme_drop = daily_return < -0.03
    extreme_volume = vol_ratio > 3.0
    extreme_rsi = rsi < 15.0

    conditions = 0
    if extreme_drop:
        conditions += 1
    if extreme_volume:
        conditions += 1
    if extreme_rsi:
        conditions += 1

    if conditions == 3:
        return 0.95  # Full capitulation = bullish contrarian signal
    elif conditions == 2:
        return 0.75
    elif conditions == 1:
        if extreme_rsi:
            return 0.6
        return 0.5

    return 0.5
