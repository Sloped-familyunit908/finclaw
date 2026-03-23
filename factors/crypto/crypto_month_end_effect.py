"""
Factor: crypto_month_end_effect
Description: Volatility/volume increase near month boundaries (estimated from idx)
Category: crypto
"""

FACTOR_NAME = "crypto_month_end_effect"
FACTOR_DESC = "Month-end effect — increased activity near month boundaries"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = likely near month end with increased activity."""
    if idx < 48:
        return 0.5

    # Approximate month boundaries: ~720 hours per month
    month_pos = idx % 720
    # Near month start (first 48h) or month end (last 48h)
    near_boundary = month_pos < 48 or month_pos > 672

    if not near_boundary:
        return 0.5

    # Check if volume is elevated vs 48h average
    avg_vol = sum(volumes[idx - 48:idx]) / 48
    if avg_vol <= 0:
        return 0.5

    vol_ratio = volumes[idx] / avg_vol
    # Check if volatility is elevated
    recent_range = 0.0
    for i in range(idx - 12, idx):
        if lows[i] > 0:
            recent_range += (highs[i] - lows[i]) / lows[i]
    recent_range /= 12

    earlier_range = 0.0
    for i in range(idx - 48, idx - 36):
        if lows[i] > 0:
            earlier_range += (highs[i] - lows[i]) / lows[i]
    earlier_range /= 12

    if earlier_range <= 0:
        return 0.5

    activity = (vol_ratio * 0.5 + (recent_range / earlier_range) * 0.5)
    score = min(1.0, activity / 2.0)
    return max(0.0, min(1.0, score))
