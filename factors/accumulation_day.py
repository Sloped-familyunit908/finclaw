"""
Auto-generated factor: accumulation_day
Description: Price up on higher-than-average volume (institutions buying)
Category: fundamental_proxy
Generated: seed
"""

FACTOR_NAME = "accumulation_day"
FACTOR_DESC = "Price up on higher-than-average volume (institutions buying)"
FACTOR_CATEGORY = "fundamental_proxy"


def compute(closes, highs, lows, volumes, idx):
    """Detect accumulation day: price up on above-average volume."""

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

    # Accumulation day: price up AND volume above average
    if daily_return > 0.002 and vol_ratio > 1.0:
        # Bullish: more buying pressure = higher score
        strength = daily_return * 5.0 * vol_ratio
        score = 0.5 + strength
        return max(0.0, min(1.0, score))

    return 0.5
