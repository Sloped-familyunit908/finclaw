FACTOR_NAME = "overnight_return"
FACTOR_DESC = "Average overnight return (open/prev_close - 1) over last 5 days"
FACTOR_CATEGORY = "gap_analysis"
LOOKBACK = 6

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    total = 0.0
    count = 0
    for i in range(idx - 4, idx + 1):
        if i < 1 or closes[i - 1] == 0:
            continue
        # Approximate open as midpoint of (prev_close, first price action)
        # Use low if gap up, high if gap down, else prev_close
        prev_c = closes[i - 1]
        # Overnight return approximated by: how much of today's range is above prev close
        overnight = (closes[i] - prev_c) / prev_c - (closes[i] - closes[i - 1]) / prev_c if prev_c != 0 else 0
        # Simpler: just use the gap component
        if lows[i] > prev_c:
            overnight = (lows[i] - prev_c) / prev_c
        elif highs[i] < prev_c:
            overnight = (highs[i] - prev_c) / prev_c
        else:
            overnight = 0.0
        total += overnight
        count += 1
    if count == 0:
        return 0.5
    avg = total / count
    score = 0.5 + avg * 50.0
    return max(0.0, min(1.0, score))
