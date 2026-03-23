"""
Factor: crypto_bounce_strength
Description: Magnitude of bounce from recent low
Category: crypto
"""

FACTOR_NAME = "crypto_bounce_strength"
FACTOR_DESC = "Strength of price bounce from recent 24h low"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = strong bounce from recent low."""
    lookback = 24
    if idx < lookback:
        return 0.5

    recent_low = min(lows[idx - lookback:idx])
    if recent_low <= 0:
        return 0.5

    # How much has price bounced from the low?
    bounce = (closes[idx] - recent_low) / recent_low

    # Also check: was the low significant? (was there a meaningful drop first?)
    recent_high = max(highs[idx - lookback:idx])
    drop = (recent_high - recent_low) / recent_high if recent_high > 0 else 0

    if drop < 0.005:  # Less than 0.5% drop isn't meaningful
        return 0.5

    # Bounce as fraction of the drop
    bounce_ratio = bounce / drop if drop > 0 else 0

    # Map: 0% bounce → 0.0, 50% bounce → 0.5, 100%+ bounce → 1.0
    score = min(bounce_ratio, 1.0)
    return max(0.0, min(1.0, score))
