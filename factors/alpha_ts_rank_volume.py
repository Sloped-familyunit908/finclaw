FACTOR_NAME = "alpha_ts_rank_volume"
FACTOR_DESC = "Time-series rank of today's volume in last 20 days"
FACTOR_CATEGORY = "alpha101"
LOOKBACK = 20

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    today_vol = volumes[idx]
    count_below = 0
    for i in range(idx - LOOKBACK + 1, idx + 1):
        if volumes[i] < today_vol:
            count_below += 1
    score = count_below / LOOKBACK
    return max(0.0, min(1.0, score))
