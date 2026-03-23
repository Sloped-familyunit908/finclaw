"""
Factor: crypto_breakout_volume
Description: Price breaks 48h range + volume >1.5x avg
Category: crypto
"""

FACTOR_NAME = "crypto_breakout_volume"
FACTOR_DESC = "Price breaks 48h range with above-average volume — confirmed breakout"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = bullish breakout, Low = bearish breakdown."""
    lookback = 48
    if idx < lookback:
        return 0.5

    # 48h range (excluding current bar)
    range_high = max(highs[idx - lookback:idx])
    range_low = min(lows[idx - lookback:idx])

    if range_high <= range_low:
        return 0.5

    # Average volume
    avg_vol = sum(volumes[idx - lookback:idx]) / lookback
    if avg_vol <= 0:
        return 0.5

    vol_ratio = volumes[idx] / avg_vol
    vol_confirmed = vol_ratio > 1.5

    current = closes[idx]

    if current > range_high:
        # Bullish breakout
        breakout_pct = (current - range_high) / (range_high - range_low) if (range_high - range_low) > 0 else 0
        strength = min(breakout_pct, 1.0)
        if vol_confirmed:
            score = 0.5 + strength * 0.45 + 0.05
        else:
            score = 0.5 + strength * 0.15  # Weaker without volume
    elif current < range_low:
        # Bearish breakdown
        breakdown_pct = (range_low - current) / (range_high - range_low) if (range_high - range_low) > 0 else 0
        strength = min(breakdown_pct, 1.0)
        if vol_confirmed:
            score = 0.5 - strength * 0.45 - 0.05
        else:
            score = 0.5 - strength * 0.15
    else:
        # Within range
        position = (current - range_low) / (range_high - range_low)
        score = 0.4 + position * 0.2  # Slightly based on position

    return max(0.0, min(1.0, score))
