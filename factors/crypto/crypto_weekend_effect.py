"""
Factor: crypto_weekend_effect
Description: Weekend vs weekday volume/volatility difference
Category: crypto
"""

FACTOR_NAME = "crypto_weekend_effect"
FACTOR_DESC = "Weekend effect — crypto trades on weekends but liquidity drops, creating different dynamics"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """
    Detects weekend vs weekday regime based on volume patterns.
    Weekend crypto: lower volume, wider spreads, more volatile.
    Uses a rolling 168h (7 days) window to detect weekly volume cycle.
    
    Returns >0.5 during weekday-like volume (higher confidence),
    <0.5 during weekend-like volume (lower confidence, mean-revert bias).
    """
    lookback_week = 168  # 7 days * 24 hours
    if idx < lookback_week:
        return 0.5

    # Calculate average volume for full week
    week_vol = sum(volumes[idx - lookback_week:idx]) / lookback_week
    if week_vol <= 0:
        return 0.5

    # Current 24h average volume
    recent_24h_vol = sum(volumes[max(0, idx - 24):idx]) / min(24, idx)
    if recent_24h_vol <= 0:
        return 0.5

    # Volume ratio: current 24h vs weekly average
    vol_ratio = recent_24h_vol / week_vol

    # <0.7 = weekend-like (low liquidity) -> 0.3, 1.0 = normal -> 0.5, >1.3 = high activity -> 0.7
    score = 0.5 + (vol_ratio - 1.0) * 0.5
    return max(0.0, min(1.0, score))
