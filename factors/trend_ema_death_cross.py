"""
Factor: trend_ema_death_cross
Description: EMA(5) crosses below EMA(20) — bearish death cross
Category: trend_following
"""

FACTOR_NAME = "trend_ema_death_cross"
FACTOR_DESC = "EMA(5) crosses below EMA(20) — bearish trend signal"
FACTOR_CATEGORY = "trend_following"


def _calc_ema(closes, end_idx, period):
    """Calculate EMA at a given index."""
    if end_idx < period:
        return sum(closes[:end_idx + 1]) / (end_idx + 1)
    multiplier = 2.0 / (period + 1)
    ema = sum(closes[:period]) / period
    for i in range(period, end_idx + 1):
        ema = (closes[i] - ema) * multiplier + ema
    return ema


def compute(closes, highs, lows, volumes, idx):
    """EMA(5) crosses below EMA(20). Score based on recency and strength.
    High score = bearish signal (death cross occurred).
    """
    if idx < 21:
        return 0.5

    ema5_now = _calc_ema(closes, idx, 5)
    ema20_now = _calc_ema(closes, idx, 20)
    ema5_prev = _calc_ema(closes, idx - 1, 5)
    ema20_prev = _calc_ema(closes, idx - 1, 20)

    # Check for death cross (EMA5 crosses below EMA20)
    crossed_today = ema5_prev >= ema20_prev and ema5_now < ema20_now

    if crossed_today:
        if ema20_now > 0:
            strength = (ema20_now - ema5_now) / ema20_now
            score = 0.85 + min(0.15, strength * 10)
        else:
            score = 0.85
        return max(0.0, min(1.0, score))

    # Check if cross happened in last 5 days
    if ema5_now < ema20_now:
        for lookback in range(1, 6):
            if idx - lookback < 20:
                break
            e5 = _calc_ema(closes, idx - lookback, 5)
            e20 = _calc_ema(closes, idx - lookback, 20)
            if e5 >= e20:
                recency = 1.0 - lookback / 5.0
                score = 0.65 + 0.2 * recency
                return max(0.0, min(1.0, score))

        return 0.6

    return 0.5  # EMA5 above EMA20 — no death cross
