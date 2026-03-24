"""
Factor: trend_ma_fan_bullish
Description: MA5 > MA10 > MA20 > MA60 fan-out pattern — strong bull trend
Category: trend_following
"""

FACTOR_NAME = "trend_ma_fan_bullish"
FACTOR_DESC = "MA5 > MA10 > MA20 > MA60 bullish fan — all MAs aligned bullish"
FACTOR_CATEGORY = "trend_following"


def _calc_ma(closes, end_idx, period):
    """Simple moving average."""
    if end_idx < period - 1:
        return None
    return sum(closes[end_idx - period + 1 : end_idx + 1]) / period


def compute(closes, highs, lows, volumes, idx):
    """MA5 > MA10 > MA20 > MA60 'fan out' pattern.
    Score based on how many consecutive MA ordering conditions hold.
    """
    if idx < 59:
        return 0.5

    ma5 = _calc_ma(closes, idx, 5)
    ma10 = _calc_ma(closes, idx, 10)
    ma20 = _calc_ma(closes, idx, 20)
    ma60 = _calc_ma(closes, idx, 60)

    if None in (ma5, ma10, ma20, ma60):
        return 0.5

    # Check ordering: MA5 > MA10 > MA20 > MA60
    ordered_pairs = 0
    total_pairs = 3

    if ma5 > ma10:
        ordered_pairs += 1
    if ma10 > ma20:
        ordered_pairs += 1
    if ma20 > ma60:
        ordered_pairs += 1

    if ordered_pairs == 0:
        return 0.0  # Completely bearish alignment
    elif ordered_pairs == total_pairs:
        # Perfect fan — check spread quality
        if ma60 > 0:
            spread = (ma5 - ma60) / ma60  # How spread out is the fan
            spread_score = min(1.0, spread / 0.10)  # 10% spread = max
        else:
            spread_score = 0.5
        score = 0.8 + 0.2 * spread_score
    else:
        # Partial ordering
        score = ordered_pairs / total_pairs * 0.7

    return max(0.0, min(1.0, score))
