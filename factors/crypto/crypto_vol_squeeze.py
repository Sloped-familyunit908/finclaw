"""
Factor: crypto_vol_squeeze
Description: Bollinger bandwidth contracting then expanding — volatility squeeze
Category: crypto
"""

FACTOR_NAME = "crypto_vol_squeeze"
FACTOR_DESC = "Bollinger bandwidth squeeze — contraction followed by expansion signals breakout"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = squeeze releasing upward, Low = releasing downward."""
    import math

    lookback = 24
    if idx < lookback + 6:
        return 0.5

    def bollinger_bandwidth(data, end, period=20):
        start = end - period + 1
        if start < 0:
            return None
        window = data[start:end + 1]
        mean = sum(window) / len(window)
        if mean <= 0:
            return None
        var = sum((x - mean) ** 2 for x in window) / len(window)
        std = math.sqrt(var) if var > 0 else 0
        return (2 * std) / mean  # Bandwidth as fraction of mean

    # Current and recent bandwidths
    bw_current = bollinger_bandwidth(closes, idx, 20)
    bw_prev = bollinger_bandwidth(closes, idx - 6, 20)

    if bw_current is None or bw_prev is None:
        return 0.5

    # Squeeze: bandwidth was contracting, now expanding
    if bw_prev > 0:
        bw_ratio = bw_current / bw_prev
    else:
        return 0.5

    # Direction of expansion
    price_direction = closes[idx] - closes[idx - 3]

    if bw_ratio > 1.3:
        # Bandwidth expanding (squeeze releasing)
        expansion_strength = min((bw_ratio - 1.0) / 1.0, 1.0)
        if price_direction > 0:
            score = 0.5 + expansion_strength * 0.4
        else:
            score = 0.5 - expansion_strength * 0.4
    elif bw_ratio < 0.7:
        # Bandwidth contracting (squeeze forming) — neutral, slight bullish bias (breakout coming)
        score = 0.55
    else:
        score = 0.5

    return max(0.0, min(1.0, score))
