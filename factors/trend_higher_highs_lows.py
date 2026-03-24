"""
Factor: trend_higher_highs_lows
Description: Count of higher highs and higher lows — uptrend strength
Category: trend_following
"""

FACTOR_NAME = "trend_higher_highs_lows"
FACTOR_DESC = "Count of higher highs AND higher lows in last 10 bars — uptrend strength"
FACTOR_CATEGORY = "trend_following"


def compute(closes, highs, lows, volumes, idx):
    """Count higher highs and higher lows in last 10 bars.
    More higher highs/lows = stronger uptrend.
    Score = (higher_highs + higher_lows) / (2 * count).
    """
    lookback = 10
    if idx < lookback:
        return 0.5

    higher_highs = 0
    higher_lows = 0
    count = 0

    for i in range(idx - lookback + 1, idx + 1):
        if i == 0:
            continue
        count += 1
        if highs[i] > highs[i - 1]:
            higher_highs += 1
        if lows[i] > lows[i - 1]:
            higher_lows += 1

    if count == 0:
        return 0.5

    # Combined score: both higher highs and higher lows matter
    hh_ratio = higher_highs / count
    hl_ratio = higher_lows / count

    # Average of both ratios
    score = (hh_ratio + hl_ratio) / 2.0

    return max(0.0, min(1.0, score))
