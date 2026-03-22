"""
Factor: ma_squeeze
Description: MA5, MA10, MA20 converging (squeeze before breakout)
Category: moving_average
"""

FACTOR_NAME = "ma_squeeze"
FACTOR_DESC = "MA5, MA10, MA20 converging (squeeze before breakout)"
FACTOR_CATEGORY = "moving_average"


def compute(closes, highs, lows, volumes, idx):
    """MAs converging tightly = potential breakout coming."""
    if idx < 25:
        return 0.5

    ma5 = sum(closes[idx - 4:idx + 1]) / 5
    ma10 = sum(closes[idx - 9:idx + 1]) / 10
    ma20 = sum(closes[idx - 19:idx + 1]) / 20

    avg_ma = (ma5 + ma10 + ma20) / 3.0
    if avg_ma <= 0:
        return 0.5

    # Current spread as percentage of average MA
    max_ma = max(ma5, ma10, ma20)
    min_ma = min(ma5, ma10, ma20)
    current_spread = (max_ma - min_ma) / avg_ma

    # Compare to spread 5 days ago
    ma5_p = sum(closes[idx - 9:idx - 4]) / 5
    ma10_p = sum(closes[idx - 14:idx - 4]) / 10
    ma20_p = sum(closes[idx - 24:idx - 4]) / 20
    avg_ma_p = (ma5_p + ma10_p + ma20_p) / 3.0
    if avg_ma_p > 0:
        past_spread = (max(ma5_p, ma10_p, ma20_p) - min(ma5_p, ma10_p, ma20_p)) / avg_ma_p
    else:
        past_spread = current_spread

    # Squeeze = tight spread AND narrowing
    # Tighter = higher score (0.5% spread → 1.0, 5% spread → 0.5)
    tightness = 1.0 - min(current_spread / 0.05, 1.0)

    # Bonus for converging
    converging_bonus = 0.1 if current_spread < past_spread else 0.0

    score = 0.5 + tightness * 0.4 + converging_bonus
    return max(0.0, min(1.0, score))
