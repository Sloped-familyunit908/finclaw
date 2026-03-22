FACTOR_NAME = "gap_down_size"
FACTOR_DESC = "Size of gap down — high score when gap is being filled (bullish)"
FACTOR_CATEGORY = "gap_analysis"
LOOKBACK = 2

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    prev_close = closes[idx - 1]
    if prev_close == 0:
        return 0.5
    # Gap down: today's high < prev_close
    gap = prev_close - highs[idx]
    if gap <= 0:
        # No gap down, or gap is being filled — check if close recovering
        if closes[idx] > closes[idx - 1]:
            return 0.6
        return 0.5
    gap_pct = gap / prev_close
    # Larger unfilled gap down = more bearish; but filling = bullish
    fill_ratio = (closes[idx] - lows[idx]) / (highs[idx] - lows[idx]) if highs[idx] != lows[idx] else 0.5
    score = fill_ratio * 0.5  # Gap down present, score depends on recovery
    return max(0.0, min(1.0, score))
