"""
Auto-generated factor: reversion_pressure
Description: How stretched price is from mean x volume confirmation
Category: mean_reversion
Generated: seed
"""

FACTOR_NAME = "reversion_pressure"
FACTOR_DESC = "How stretched price is from mean x volume confirmation"
FACTOR_CATEGORY = "mean_reversion"


def compute(closes, highs, lows, volumes, idx):
    """Stretch from 20-day mean multiplied by volume ratio for confirmation."""

    lookback = 20
    if idx < lookback:
        return 0.5

    # 20-day SMA of price
    price_total = 0.0
    for i in range(idx - lookback + 1, idx + 1):
        price_total += closes[i]
    sma_price = price_total / lookback

    if sma_price < 1e-10:
        return 0.5

    # 20-day SMA of volume
    vol_total = 0.0
    for i in range(idx - lookback + 1, idx + 1):
        vol_total += volumes[i]
    sma_vol = vol_total / lookback

    # Price stretch from mean
    stretch = (closes[idx] - sma_price) / sma_price

    # Volume ratio (current vs average)
    vol_ratio = volumes[idx] / sma_vol if sma_vol > 0 else 1.0

    # Reversion pressure: stretched below mean + high volume = strong reversion setup
    # Negative stretch (oversold) with high volume = bullish reversion
    pressure = -stretch * vol_ratio

    # Map to [0, 1]: pressure in [-0.5, 0.5] range
    score = 0.5 + pressure
    return max(0.0, min(1.0, score))
