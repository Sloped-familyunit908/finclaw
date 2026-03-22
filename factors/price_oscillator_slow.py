FACTOR_NAME = "price_oscillator_slow"
FACTOR_DESC = "(EMA13 - EMA26) / EMA26 — slow price oscillator"
FACTOR_CATEGORY = "price_structure"
LOOKBACK = 26

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    # Compute EMA13
    mult13 = 2.0 / 14.0
    ema13 = closes[idx - LOOKBACK + 1]
    for i in range(idx - LOOKBACK + 2, idx + 1):
        ema13 = (closes[i] - ema13) * mult13 + ema13
    # Compute EMA26
    mult26 = 2.0 / 27.0
    ema26 = closes[idx - LOOKBACK + 1]
    for i in range(idx - LOOKBACK + 2, idx + 1):
        ema26 = (closes[i] - ema26) * mult26 + ema26
    if ema26 == 0:
        return 0.5
    osc = (ema13 - ema26) / ema26
    # Map [-0.05, 0.05] to [0, 1]
    score = 0.5 + osc * 10.0
    return max(0.0, min(1.0, score))
