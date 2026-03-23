"""
Factor: crypto_tick_intensity
Description: Range/close ratio — price level activity intensity
Category: crypto
"""

FACTOR_NAME = "crypto_tick_intensity"
FACTOR_DESC = "Range/close ratio measuring price level activity intensity"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = intense price activity."""
    lookback = 24
    if idx < lookback:
        return 0.5

    # Current bar intensity
    if closes[idx] <= 0:
        return 0.5

    current_intensity = (highs[idx] - lows[idx]) / closes[idx]

    # Historical intensity for percentile ranking
    intensities = []
    for i in range(idx - lookback, idx + 1):
        if closes[i] > 0:
            intensities.append((highs[i] - lows[i]) / closes[i])

    if len(intensities) < 5:
        return 0.5

    # Percentile rank of current intensity
    rank = sum(1 for x in intensities if x <= current_intensity)
    score = rank / len(intensities)

    return max(0.0, min(1.0, score))
