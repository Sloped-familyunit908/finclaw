"""
Factor: smart_money_index
Description: Compare first-30-min vs last-hour price action proxy
Category: volume
"""

FACTOR_NAME = "smart_money_index"
FACTOR_DESC = "Smart money index — proxy using open/close/mid relationships"
FACTOR_CATEGORY = "volume"


def compute(closes, highs, lows, volumes, idx):
    """
    Smart money proxy using daily data:
    - Dumb money trades at open (emotional, gap reactions)
    - Smart money trades at close (informed, deliberate)
    
    Proxy: open_move = |open - prev_close| (emotional reaction)
    close_move = close direction vs intraday mid
    
    Since we don't have opens directly, use: mid = (high + low) / 2
    If close > mid = smart money buying (they pushed close up from mid)
    """
    lookback = 10
    if idx < lookback:
        return 0.5

    smart_score = 0.0
    for i in range(idx - lookback + 1, idx + 1):
        mid = (highs[i] + lows[i]) / 2.0
        day_range = highs[i] - lows[i]
        if day_range <= 0:
            continue

        # Where close sits relative to midpoint
        close_position = (closes[i] - mid) / day_range
        smart_score += close_position

    # Average over lookback
    smart_score /= lookback

    # Normalize: -0.5 → 0.0, 0 → 0.5, +0.5 → 1.0
    score = 0.5 + smart_score

    return max(0.0, min(1.0, score))
