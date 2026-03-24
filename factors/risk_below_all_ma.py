"""
Factor: risk_below_all_ma
Description: Price below MA5, MA10, MA20, MA60 — death zone
Category: risk_warning
"""

FACTOR_NAME = "risk_below_all_ma"
FACTOR_DESC = "Price below all MAs (5/10/20/60) — death zone, every MA is resistance"
FACTOR_CATEGORY = "risk_warning"


def _calc_ma(closes, end_idx, period):
    """Simple moving average."""
    if end_idx < period - 1:
        return None
    return sum(closes[end_idx - period + 1 : end_idx + 1]) / period


def compute(closes, highs, lows, volumes, idx):
    """Score based on how many MAs price is below.
    All 4 below = 1.0 (maximum risk), none = 0.0.
    """
    if idx < 60:
        periods = [p for p in [5, 10, 20, 60] if idx >= p - 1]
        if not periods:
            return 0.5
    else:
        periods = [5, 10, 20, 60]

    below_count = 0
    total = len(periods)

    for period in periods:
        ma = _calc_ma(closes, idx, period)
        if ma is not None and closes[idx] < ma:
            below_count += 1

    if total == 0:
        return 0.5

    score = below_count / total

    return max(0.0, min(1.0, score))
