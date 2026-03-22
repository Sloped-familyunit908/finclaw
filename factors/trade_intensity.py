"""
Auto-generated factor: trade_intensity
Description: Volume / (High - Low + 0.01) - trades per price range unit
Category: microstructure
Generated: seed
"""

FACTOR_NAME = "trade_intensity"
FACTOR_DESC = "Volume / (High - Low + 0.01) - trades per price range unit"
FACTOR_CATEGORY = "microstructure"


def compute(closes, highs, lows, volumes, idx):
    """Trade intensity: volume per unit of price range."""

    lookback = 10
    if idx < lookback:
        return 0.5

    # Current intensity
    current_intensity = volumes[idx] / (highs[idx] - lows[idx] + 0.01)

    # Average intensity over lookback
    total_intensity = 0.0
    for i in range(idx - lookback, idx):
        intensity = volumes[i] / (highs[i] - lows[i] + 0.01)
        total_intensity += intensity
    avg_intensity = total_intensity / lookback

    if avg_intensity < 1e-10:
        return 0.5

    # Ratio of current to average
    ratio = current_intensity / avg_intensity

    # Higher intensity (more volume per range) = more liquid = bullish
    # Map ratio from [0, 3] to [0, 1]
    score = ratio / 3.0
    return max(0.0, min(1.0, score))
