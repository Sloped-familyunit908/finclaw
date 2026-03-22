FACTOR_NAME = "gap_fill_pct"
FACTOR_DESC = "Percentage of yesterday's gap that has been filled today"
FACTOR_CATEGORY = "gap_analysis"
LOOKBACK = 2

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    prev_close = closes[idx - 1]
    if prev_close == 0:
        return 0.5
    # Check for gap up yesterday: prev low > closes[idx-2]
    if idx < 3:
        return 0.5
    prev_prev_close = closes[idx - 2]
    if prev_prev_close == 0:
        return 0.5
    # Gap up: yesterday opened above day-before-yesterday's close
    gap_up = lows[idx - 1] - prev_prev_close
    # Gap down: yesterday's high below day-before-yesterday's close
    gap_down = prev_prev_close - highs[idx - 1]
    if gap_up > 0:
        # Gap up exists — filling means price comes down toward gap
        gap_size = gap_up
        fill = max(0, prev_close - closes[idx])  # price dropped
        fill_pct = fill / gap_size if gap_size > 0 else 0
        # Gap fill on up gap is bearish, so invert
        score = 1.0 - min(1.0, fill_pct)
        return max(0.0, min(1.0, score))
    elif gap_down > 0:
        # Gap down exists — filling means price recovers
        gap_size = gap_down
        fill = max(0, closes[idx] - prev_close)
        fill_pct = fill / gap_size if gap_size > 0 else 0
        score = min(1.0, fill_pct) * 0.5 + 0.5
        return max(0.0, min(1.0, score))
    return 0.5
