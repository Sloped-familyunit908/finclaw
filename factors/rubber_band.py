"""
Auto-generated factor: rubber_band
Description: The further price stretches from MA, the stronger the snap-back force
Category: mean_reversion
Generated: seed
"""

FACTOR_NAME = "rubber_band"
FACTOR_DESC = "The further price stretches from MA, the stronger the snap-back force"
FACTOR_CATEGORY = "mean_reversion"


def compute(closes, highs, lows, volumes, idx):
    """Rubber band effect: distance from 20-day MA as snap-back force."""

    lookback = 20
    if idx < lookback:
        return 0.5

    total = 0.0
    for i in range(idx - lookback + 1, idx + 1):
        total += closes[i]
    sma = total / lookback

    if sma < 1e-10:
        return 0.5

    stretch = (closes[idx] - sma) / sma

    # Also check if stretch is increasing (acceleration)
    if idx >= lookback + 1:
        total_prev = 0.0
        for i in range(idx - lookback, idx):
            total_prev += closes[i]
        sma_prev = total_prev / lookback
        prev_stretch = (closes[idx - 1] - sma_prev) / sma_prev if sma_prev > 1e-10 else 0.0
    else:
        prev_stretch = 0.0

    # Snap-back force increases with distance
    # Oversold (negative stretch) = bullish snap-back = high score
    # Over-extended (positive stretch) = bearish snap-back = low score
    force = abs(stretch) * 5.0  # Scale factor

    if stretch < 0:
        # Below MA: bullish reversion expectation
        score = 0.5 + force
    else:
        # Above MA: bearish reversion expectation
        score = 0.5 - force

    return max(0.0, min(1.0, score))
