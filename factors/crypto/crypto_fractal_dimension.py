"""
Factor: crypto_fractal_dimension
Description: Hurst exponent proxy — determines trend vs mean-reversion regime
Category: crypto
"""

FACTOR_NAME = "crypto_fractal_dimension"
FACTOR_DESC = "Fractal dimension proxy via Hurst exponent — trend vs mean-reversion detection"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = trending (H>0.5), Low = mean-reverting (H<0.5)."""
    lookback = 48
    if idx < lookback:
        return 0.5

    prices = closes[idx - lookback:idx]
    n = len(prices)

    # Simplified rescaled range (R/S) analysis
    mean_p = sum(prices) / n

    # Cumulative deviations
    cum_devs = []
    running = 0.0
    for p in prices:
        running += p - mean_p
        cum_devs.append(running)

    r = max(cum_devs) - min(cum_devs)  # Range

    # Standard deviation
    variance = sum((p - mean_p) ** 2 for p in prices) / n
    s = variance ** 0.5

    if s <= 0 or r <= 0:
        return 0.5

    rs = r / s

    # Hurst exponent approximation: H = log(R/S) / log(n)
    import math
    if n <= 1:
        return 0.5

    h = math.log(rs) / math.log(n)

    # H > 0.5 = trending, H < 0.5 = mean-reverting, H = 0.5 = random
    # Clamp to [0, 1]
    return max(0.0, min(1.0, h))
