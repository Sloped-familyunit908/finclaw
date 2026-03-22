FACTOR_NAME = "gap_frequency"
FACTOR_DESC = "Number of gaps in last 20 days — high frequency indicates volatility"
FACTOR_CATEGORY = "gap_analysis"
LOOKBACK = 20

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    gap_count = 0
    for i in range(idx - LOOKBACK + 1, idx + 1):
        if i < 1:
            continue
        # Count any gap (up or down)
        if lows[i] > highs[i - 1] or highs[i] < lows[i - 1]:
            gap_count += 1
    # Normalize: 0 gaps = 0.5, up to 10+ gaps = 1.0
    score = 0.5 + gap_count * 0.05
    return max(0.0, min(1.0, score))
