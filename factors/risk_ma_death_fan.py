"""
Factor: risk_ma_death_fan
Description: MA5 < MA10 < MA20 < MA60 death fan — all bearish
Category: risk_warning
"""

FACTOR_NAME = "risk_ma_death_fan"
FACTOR_DESC = "MA5 < MA10 < MA20 < MA60 death fan — all trends aligned bearish"
FACTOR_CATEGORY = "risk_warning"


def _calc_ma(closes, end_idx, period):
    """Simple moving average."""
    if end_idx < period - 1:
        return None
    return sum(closes[end_idx - period + 1 : end_idx + 1]) / period


def compute(closes, highs, lows, volumes, idx):
    """MA5 < MA10 < MA20 < MA60 'death fan'.
    All moving averages aligned bearish = maximum downtrend signal.
    """
    if idx < 59:
        return 0.5

    ma5 = _calc_ma(closes, idx, 5)
    ma10 = _calc_ma(closes, idx, 10)
    ma20 = _calc_ma(closes, idx, 20)
    ma60 = _calc_ma(closes, idx, 60)

    if None in (ma5, ma10, ma20, ma60):
        return 0.5

    # Check reverse ordering: MA5 < MA10 < MA20 < MA60
    ordered_pairs = 0
    total_pairs = 3

    if ma5 < ma10:
        ordered_pairs += 1
    if ma10 < ma20:
        ordered_pairs += 1
    if ma20 < ma60:
        ordered_pairs += 1

    if ordered_pairs == 0:
        return 0.0  # Completely bullish — no risk from death fan

    if ordered_pairs == total_pairs:
        # Perfect death fan
        if ma60 > 0:
            spread = (ma60 - ma5) / ma60
            spread_score = min(1.0, spread / 0.10)
        else:
            spread_score = 0.5
        score = 0.8 + 0.2 * spread_score
    else:
        score = ordered_pairs / total_pairs * 0.7

    return max(0.0, min(1.0, score))
