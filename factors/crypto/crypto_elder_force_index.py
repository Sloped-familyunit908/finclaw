"""
Factor: crypto_elder_force_index
Description: (close - prev_close) * volume
Category: crypto
"""

FACTOR_NAME = "crypto_elder_force_index"
FACTOR_DESC = "(close - prev_close) * volume"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. >0.5 = positive force (bullish), <0.5 = negative."""
    lookback = 13
    if idx < lookback + 1:
        return 0.5

    # EMA of force index
    forces = []
    for i in range(idx - lookback, idx):
        if i < 1:
            forces.append(0)
            continue
        forces.append((closes[i] - closes[i - 1]) * volumes[i])

    avg_vol = sum(volumes[idx - lookback:idx]) / lookback if lookback > 0 else 1
    avg_price = sum(closes[idx - lookback:idx]) / lookback if lookback > 0 else 1
    normalizer = avg_vol * avg_price * 0.02

    if normalizer <= 0:
        return 0.5

    avg_force = sum(forces) / len(forces)
    score = 0.5 + (avg_force / normalizer) * 0.5
    return max(0.0, min(1.0, score))
