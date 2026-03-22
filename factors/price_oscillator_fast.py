FACTOR_NAME = "price_oscillator_fast"
FACTOR_DESC = "(EMA5 - EMA13) / EMA13 — fast price oscillator"
FACTOR_CATEGORY = "price_structure"
LOOKBACK = 13

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    # Compute EMA5
    mult5 = 2.0 / 6.0
    ema5 = closes[idx - LOOKBACK + 1]
    for i in range(idx - LOOKBACK + 2, idx + 1):
        ema5 = (closes[i] - ema5) * mult5 + ema5
    # Compute EMA13
    mult13 = 2.0 / 14.0
    ema13 = closes[idx - LOOKBACK + 1]
    for i in range(idx - LOOKBACK + 2, idx + 1):
        ema13 = (closes[i] - ema13) * mult13 + ema13
    if ema13 == 0:
        return 0.5
    osc = (ema5 - ema13) / ema13
    # Map [-0.05, 0.05] to [0, 1]
    score = 0.5 + osc * 10.0
    return max(0.0, min(1.0, score))
