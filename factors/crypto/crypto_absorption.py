"""
Factor: crypto_absorption
Description: High volume with small price change — orders being absorbed
Category: crypto
"""

FACTOR_NAME = "crypto_absorption"
FACTOR_DESC = "High volume with small price change — order absorption detection"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = buying absorbed (support), Low = selling absorbed (resistance)."""
    lookback = 24
    if idx < lookback:
        return 0.5

    avg_vol = sum(volumes[idx - lookback:idx]) / lookback
    if avg_vol <= 0:
        return 0.5

    vol_ratio = volumes[idx] / avg_vol
    if closes[idx - 1] <= 0:
        return 0.5

    pct_move = abs(closes[idx] - closes[idx - 1]) / closes[idx - 1]

    # High volume (>2x avg) but small move (<0.3%) = absorption
    if vol_ratio < 2.0 or pct_move > 0.003:
        return 0.5

    # Check trend direction leading in: was price falling or rising?
    trend = (closes[idx] - closes[idx - 4]) / closes[idx - 4] if closes[idx - 4] > 0 else 0

    # Absorption after downtrend = support being built = bullish
    # Absorption after uptrend = resistance being hit = bearish
    absorption_strength = min(vol_ratio / 6.0, 1.0)
    if trend < -0.005:
        # Downtrend absorbed → bullish
        score = 0.5 + absorption_strength * 0.4
    elif trend > 0.005:
        # Uptrend absorbed → bearish
        score = 0.5 - absorption_strength * 0.4
    else:
        score = 0.5

    return max(0.0, min(1.0, score))
