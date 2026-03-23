"""
Factor: crypto_whale_candle
Description: Detects single candle with >5x avg volume and >1% price move — whale activity
Category: crypto
"""

FACTOR_NAME = "crypto_whale_candle"
FACTOR_DESC = "Single candle >5x avg volume + >1% move — whale activity signal"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = whale buying, Low = whale selling."""
    lookback = 24
    if idx < lookback:
        return 0.5

    avg_vol = sum(volumes[idx - lookback:idx]) / lookback
    if avg_vol <= 0:
        return 0.5

    vol_ratio = volumes[idx] / avg_vol
    if closes[idx - 1] <= 0:
        return 0.5

    pct_move = (closes[idx] - closes[idx - 1]) / closes[idx - 1]

    # Need >5x volume AND >1% move to qualify as whale candle
    if vol_ratio < 5.0 or abs(pct_move) < 0.01:
        return 0.5

    # Direction: positive move = bullish whale, negative = bearish whale
    # Scale by magnitude of move (capped at 5%)
    intensity = min(abs(pct_move) / 0.05, 1.0)
    if pct_move > 0:
        score = 0.5 + intensity * 0.5
    else:
        score = 0.5 - intensity * 0.5

    return max(0.0, min(1.0, score))
