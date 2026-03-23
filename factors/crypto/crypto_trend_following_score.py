"""
Factor: crypto_trend_following_score
Description: Multi-indicator trend following signal
Category: crypto
"""

FACTOR_NAME = "crypto_trend_following_score"
FACTOR_DESC = "Multi-indicator trend following signal"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. >0.5 = trend following buy, <0.5 = sell."""
    if idx < 50:
        return 0.5

    score = 0.0
    weights = 0.0

    # 1. Price vs EMA20 (weight 0.3)
    mult = 2.0 / 21
    ema20 = closes[idx - 21]
    for i in range(idx - 20, idx):
        ema20 = closes[i] * mult + ema20 * (1 - mult)
    if ema20 > 0:
        s = 1.0 if closes[idx - 1] > ema20 else 0.0
        score += s * 0.3
        weights += 0.3

    # 2. ADX proxy: directional movement (weight 0.3)
    plus_dm = 0.0
    minus_dm = 0.0
    for i in range(idx - 14, idx):
        if i < 1:
            continue
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        if up > down and up > 0:
            plus_dm += up
        if down > up and down > 0:
            minus_dm += down
    total_dm = plus_dm + minus_dm
    if total_dm > 0:
        s = plus_dm / total_dm
        score += s * 0.3
        weights += 0.3

    # 3. Higher highs + higher lows (weight 0.2)
    hh = highs[idx - 1] > highs[idx - 2] if idx > 1 else False
    hl = lows[idx - 1] > lows[idx - 2] if idx > 1 else False
    s = (1.0 if hh else 0.0) * 0.5 + (1.0 if hl else 0.0) * 0.5
    score += s * 0.2
    weights += 0.2

    # 4. Volume confirmation (weight 0.2)
    avg_vol = sum(volumes[idx - 24:idx]) / 24
    vol_up = volumes[idx - 1] > avg_vol
    price_up = closes[idx - 1] > closes[idx - 2] if idx > 1 else False
    s = 1.0 if (vol_up and price_up) else (0.0 if (vol_up and not price_up) else 0.5)
    score += s * 0.2
    weights += 0.2

    if weights <= 0:
        return 0.5

    return max(0.0, min(1.0, score / weights))
