FACTOR_NAME = "trix"
FACTOR_DESC = "Triple EMA rate of change — very smooth momentum indicator"
FACTOR_CATEGORY = "price_structure"
LOOKBACK = 45

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    mult = 2.0 / 16.0  # 15-period EMA
    # First EMA
    ema1 = closes[idx - LOOKBACK + 1]
    for i in range(idx - LOOKBACK + 2, idx + 1):
        ema1_prev = ema1
        ema1 = (closes[i] - ema1) * mult + ema1
    # Second EMA (of first EMA) — recompute
    ema1_series = [closes[idx - LOOKBACK + 1]]
    val = closes[idx - LOOKBACK + 1]
    for i in range(idx - LOOKBACK + 2, idx + 1):
        val = (closes[i] - val) * mult + val
        ema1_series.append(val)
    ema2 = ema1_series[0]
    ema2_series = [ema2]
    for i in range(1, len(ema1_series)):
        ema2 = (ema1_series[i] - ema2) * mult + ema2
        ema2_series.append(ema2)
    # Third EMA (of second EMA)
    ema3_prev = ema2_series[0]
    ema3_prev2 = ema3_prev
    for i in range(1, len(ema2_series)):
        ema3_prev2 = ema3_prev
        ema3_prev = (ema2_series[i] - ema3_prev) * mult + ema3_prev
    # TRIX = rate of change of triple EMA
    if ema3_prev2 == 0:
        return 0.5
    trix_val = (ema3_prev - ema3_prev2) / ema3_prev2
    # Map [-0.01, 0.01] to [0, 1]
    score = 0.5 + trix_val * 50.0
    return max(0.0, min(1.0, score))
