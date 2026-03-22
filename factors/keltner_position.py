"""
Factor: keltner_position
Description: Price position within Keltner Channel (EMA ± ATR)
Category: volatility
"""

FACTOR_NAME = "keltner_position"
FACTOR_DESC = "Price position within Keltner Channel (EMA ± 2*ATR)"
FACTOR_CATEGORY = "volatility"


def compute(closes, highs, lows, volumes, idx):
    """Position within Keltner Channel: EMA20 ± 2*ATR10."""
    ema_period = 20
    atr_period = 10
    if idx < max(ema_period, atr_period) + 1:
        return 0.5

    # Simple MA as EMA proxy (no imports allowed)
    ema = sum(closes[idx - ema_period + 1:idx + 1]) / ema_period

    # ATR
    tr_sum = 0.0
    for i in range(idx - atr_period + 1, idx + 1):
        tr1 = highs[i] - lows[i]
        tr2 = abs(highs[i] - closes[i - 1])
        tr3 = abs(lows[i] - closes[i - 1])
        tr_sum += max(tr1, tr2, tr3)
    atr = tr_sum / atr_period

    if atr <= 0:
        return 0.5

    upper = ema + 2.0 * atr
    lower = ema - 2.0 * atr
    channel_width = upper - lower

    if channel_width <= 0:
        return 0.5

    position = (closes[idx] - lower) / channel_width

    return max(0.0, min(1.0, position))
