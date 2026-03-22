FACTOR_NAME = "unfilled_gap_up"
FACTOR_DESC = "Unfilled gap up within last 10 days acts as support below — bullish"
FACTOR_CATEGORY = "gap_analysis"
LOOKBACK = 11

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    # Look for unfilled gap ups in last 10 days
    gap_count = 0
    for i in range(idx - 9, idx + 1):
        if i < 1:
            continue
        prev_c = closes[i - 1]
        if prev_c == 0:
            continue
        # Gap up: today's low > yesterday's high (strict gap)
        if lows[i] > highs[i - 1]:
            # Check if gap has been filled since
            filled = False
            for j in range(i + 1, idx + 1):
                if lows[j] <= highs[i - 1]:
                    filled = True
                    break
            if not filled:
                gap_count += 1
    # More unfilled gap ups = more support = bullish
    score = 0.5 + gap_count * 0.15
    return max(0.0, min(1.0, score))
