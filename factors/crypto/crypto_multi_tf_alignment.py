"""
Factor: crypto_multi_tf_alignment
Description: 1h/4h/24h EMA direction agreement
Category: crypto
"""

FACTOR_NAME = "crypto_multi_tf_alignment"
FACTOR_DESC = "Multi-timeframe EMA alignment — 1h/4h/24h trend agreement"
FACTOR_CATEGORY = "crypto"


def _ema(data, period, end_idx):
    """Compute EMA ending at end_idx."""
    start = max(0, end_idx - period * 3)
    multiplier = 2.0 / (period + 1)
    ema = data[start]
    for i in range(start + 1, end_idx + 1):
        ema = (data[i] - ema) * multiplier + ema
    return ema


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = all timeframes bullish, Low = all bearish."""
    if idx < 48:
        return 0.5

    # 1h trend: price vs 4-bar EMA
    ema_1h = _ema(closes, 4, idx)
    trend_1h = 1 if closes[idx] > ema_1h else -1

    # 4h trend: price vs 16-bar EMA (4h * 4)
    ema_4h = _ema(closes, 16, idx)
    trend_4h = 1 if closes[idx] > ema_4h else -1

    # 24h trend: price vs 24-bar EMA
    ema_24h = _ema(closes, 24, idx)
    trend_24h = 1 if closes[idx] > ema_24h else -1

    alignment = trend_1h + trend_4h + trend_24h

    # -3 = all bearish, +3 = all bullish
    # Map [-3, 3] → [0, 1]
    score = (alignment + 3) / 6.0

    return max(0.0, min(1.0, score))
