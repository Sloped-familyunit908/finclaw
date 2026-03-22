FACTOR_NAME = "unfilled_gap_down"
FACTOR_DESC = "Unfilled gap down within last 10 days acts as resistance above — bearish"
FACTOR_CATEGORY = "gap_analysis"
LOOKBACK = 11

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    gap_count = 0
    for i in range(idx - 9, idx + 1):
        if i < 1:
            continue
        # Gap down: today's high < yesterday's low (strict gap)
        if highs[i] < lows[i - 1]:
            filled = False
            for j in range(i + 1, idx + 1):
                if highs[j] >= lows[i - 1]:
                    filled = True
                    break
            if not filled:
                gap_count += 1
    # More unfilled gap downs = more resistance = bearish
    score = 0.5 - gap_count * 0.15
    return max(0.0, min(1.0, score))
