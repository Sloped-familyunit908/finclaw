FACTOR_NAME = "gap_continuation"
FACTOR_DESC = "Gap up that continues — opens above prev close and closes above open"
FACTOR_CATEGORY = "gap_analysis"
LOOKBACK = 2

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    prev_c = closes[idx - 1]
    if prev_c == 0:
        return 0.5
    # Gap up: today's low > prev_close, and close > low (continuation)
    if lows[idx] > prev_c and closes[idx] > lows[idx]:
        gap_pct = (lows[idx] - prev_c) / prev_c
        continuation = (closes[idx] - lows[idx]) / prev_c
        score = 0.6 + (gap_pct + continuation) * 5.0
        return max(0.0, min(1.0, score))
    elif closes[idx] > prev_c and closes[idx] > closes[idx - 1]:
        # Mild continuation without strict gap
        ret = (closes[idx] - prev_c) / prev_c
        score = 0.5 + ret * 5.0
        return max(0.0, min(1.0, score))
    return 0.5
