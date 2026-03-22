"""
Auto-generated factor: distribution_day
Description: Price down on higher-than-average volume (institutions selling)
Category: fundamental_proxy
Generated: seed
"""

FACTOR_NAME = "distribution_day"
FACTOR_DESC = "Price down on higher-than-average volume (institutions selling)"
FACTOR_CATEGORY = "fundamental_proxy"


def compute(closes, highs, lows, volumes, idx):
    """Detect distribution day: price down on above-average volume."""

    lookback = 20
    if idx < lookback:
        return 0.5

    # Average volume
    vol_total = 0.0
    for i in range(idx - lookback, idx):
        vol_total += volumes[i]
    avg_vol = vol_total / lookback

    # Today's return
    daily_return = (closes[idx] - closes[idx - 1]) / closes[idx - 1] if closes[idx - 1] > 0 else 0.0

    # Volume ratio
    vol_ratio = volumes[idx] / avg_vol if avg_vol > 0 else 1.0

    # Distribution day: price down AND volume above average
    if daily_return < -0.002 and vol_ratio > 1.0:
        # Bearish: more selling pressure = lower score
        severity = abs(daily_return) * 5.0 * vol_ratio
        score = 0.5 - severity
        return max(0.0, min(1.0, score))

    return 0.5
