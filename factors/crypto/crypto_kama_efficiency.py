"""
Factor: crypto_kama_efficiency
Description: Kaufman Adaptive MA efficiency ratio
Category: crypto
"""

FACTOR_NAME = "crypto_kama_efficiency"
FACTOR_DESC = "Kaufman Adaptive MA efficiency ratio"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = efficient (trending), low = noisy."""
    lookback = 10
    if idx < lookback + 1:
        return 0.5

    # Direction (signal)
    signal = abs(closes[idx - 1] - closes[idx - lookback - 1])

    # Noise (sum of absolute changes)
    noise = 0.0
    for i in range(idx - lookback, idx):
        if i < 1:
            continue
        noise += abs(closes[i] - closes[i - 1])

    if noise <= 0:
        return 0.5

    er = signal / noise
    return max(0.0, min(1.0, er))
