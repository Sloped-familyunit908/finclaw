"""
Factor: atr_channel_position
Description: Where price is within ATR-based channel
Category: volatility
"""

FACTOR_NAME = "atr_channel_position"
FACTOR_DESC = "Price position within ATR-based channel"
FACTOR_CATEGORY = "volatility"


def compute(closes, highs, lows, volumes, idx):
    """Position within channel: MA20 ± 2*ATR14."""
    atr_period = 14
    ma_period = 20
    if idx < max(atr_period, ma_period) + 1:
        return 0.5

    # Calculate ATR (Average True Range)
    tr_sum = 0.0
    for i in range(idx - atr_period + 1, idx + 1):
        tr1 = highs[i] - lows[i]
        tr2 = abs(highs[i] - closes[i - 1])
        tr3 = abs(lows[i] - closes[i - 1])
        tr = max(tr1, tr2, tr3)
        tr_sum += tr
    atr = tr_sum / atr_period

    # MA20
    ma = sum(closes[idx - ma_period + 1:idx + 1]) / ma_period

    if atr <= 0:
        return 0.5

    # Channel: MA ± 2*ATR
    upper = ma + 2.0 * atr
    lower = ma - 2.0 * atr
    channel_width = upper - lower

    if channel_width <= 0:
        return 0.5

    # Position within channel (0 = at lower band, 1 = at upper band)
    position = (closes[idx] - lower) / channel_width

    return max(0.0, min(1.0, position))
