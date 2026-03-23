"""
Factor: crypto_pullback_buy
Description: After rally, 2-5% pullback on declining volume — buy signal
Category: crypto
"""

FACTOR_NAME = "crypto_pullback_buy"
FACTOR_DESC = "2-5% pullback after rally on declining volume — pullback buy setup"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = good pullback buy setup."""
    lookback = 24
    if idx < lookback:
        return 0.5

    # Find recent swing high (highest close in last 24 bars)
    swing_high = max(closes[idx - lookback:idx])
    swing_high_idx = idx - lookback
    for i in range(idx - lookback, idx):
        if closes[i] == swing_high:
            swing_high_idx = i

    if swing_high <= 0:
        return 0.5

    # Check if there was a rally before the swing high (>5% up from earlier)
    rally_lookback = min(swing_high_idx, 24)
    if rally_lookback < 6:
        return 0.5

    pre_rally_price = closes[swing_high_idx - rally_lookback]
    if pre_rally_price <= 0:
        return 0.5

    rally_pct = (swing_high - pre_rally_price) / pre_rally_price

    if rally_pct < 0.05:
        # No significant rally
        return 0.5

    # Current pullback from swing high
    pullback_pct = (swing_high - closes[idx]) / swing_high

    # Check volume declining during pullback
    if swing_high_idx >= idx:
        return 0.5

    pullback_bars = idx - swing_high_idx
    if pullback_bars < 2:
        return 0.5

    avg_vol_rally = sum(volumes[max(0, swing_high_idx - 6):swing_high_idx]) / max(1, min(6, swing_high_idx))
    avg_vol_pullback = sum(volumes[swing_high_idx:idx + 1]) / pullback_bars
    vol_declining = avg_vol_pullback < avg_vol_rally * 0.8 if avg_vol_rally > 0 else False

    # Ideal: 2-5% pullback on declining volume
    if 0.02 <= pullback_pct <= 0.05 and vol_declining:
        # Perfect setup
        score = 0.75 + min(rally_pct / 0.2, 1.0) * 0.2
    elif 0.01 <= pullback_pct <= 0.07:
        # Decent setup
        vol_bonus = 0.1 if vol_declining else 0
        score = 0.55 + vol_bonus
    else:
        score = 0.5

    return max(0.0, min(1.0, score))
