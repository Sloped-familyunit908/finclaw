"""
Quality Factor: Relative Strength 20-day
=========================================
Stock's 20-day return vs average 20-day return (shorter-term version).
Score 1.0 if outperforming by >20%, 0.0 if underperforming by >20%.

Category: quality_filter
"""

FACTOR_NAME = "quality_relative_strength_20d"
FACTOR_DESC = "20-day return vs market average — short-term relative strength"
FACTOR_CATEGORY = "quality_filter"


def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0]."""
    lookback = 20
    if idx < lookback or closes[idx - lookback] <= 0:
        return 0.5

    stock_ret = (closes[idx] - closes[idx - lookback]) / closes[idx - lookback]

    # Self-benchmark: average rolling 20d returns over available history
    count = 0
    total_ret = 0.0
    sample_start = max(lookback, idx - 120)  # look back up to 120 days for avg
    step = 3
    for i in range(sample_start, idx + 1, step):
        if i - lookback >= 0 and closes[i - lookback] > 0:
            r = (closes[i] - closes[i - lookback]) / closes[i - lookback]
            total_ret += r
            count += 1
    avg_ret = total_ret / count if count > 0 else 0.0

    diff = stock_ret - avg_ret
    # Map diff: -0.20 -> 0.0, 0.0 -> 0.5, +0.20 -> 1.0
    score = 0.5 + diff / 0.40
    return max(0.0, min(1.0, score))
