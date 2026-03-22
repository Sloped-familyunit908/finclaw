FACTOR_NAME = "intraday_return"
FACTOR_DESC = "Average intraday return (close/open - 1) over last 5 days"
FACTOR_CATEGORY = "gap_analysis"
LOOKBACK = 6

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    total = 0.0
    count = 0
    for i in range(idx - 4, idx + 1):
        if i < 1:
            continue
        # Approximate open as previous close
        opn = closes[i - 1]
        if opn == 0:
            continue
        intra_ret = (closes[i] - opn) / opn
        total += intra_ret
        count += 1
    if count == 0:
        return 0.5
    avg = total / count
    score = 0.5 + avg * 50.0
    return max(0.0, min(1.0, score))
