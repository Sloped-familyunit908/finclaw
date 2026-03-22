FACTOR_NAME = "gap_up_size"
FACTOR_DESC = "Size of gap up (open > prev_close) normalized"
FACTOR_CATEGORY = "gap_analysis"
LOOKBACK = 2

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    prev_close = closes[idx - 1]
    if prev_close == 0:
        return 0.5
    # Approximate open as: use the low if gap up, or infer from price action
    # If today's low > prev_close, there's a gap up
    gap = lows[idx] - prev_close
    if gap <= 0:
        return 0.5  # No gap up
    gap_pct = gap / prev_close
    # Map [0, 0.05] to [0.5, 1.0] — bigger gap = more bullish
    score = 0.5 + gap_pct * 10.0
    return max(0.0, min(1.0, score))
