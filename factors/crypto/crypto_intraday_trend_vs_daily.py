"""
Factor: crypto_intraday_trend_vs_daily
Description: 4h EMA direction vs 24h EMA direction — timeframe alignment
Category: crypto
"""

FACTOR_NAME = "crypto_intraday_trend_vs_daily"
FACTOR_DESC = "Alignment of 4h EMA trend vs 24h EMA trend"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = both timeframes bullish, Low = both bearish."""
    if idx < 48:
        return 0.5

    # Compute 4h and 24h EMAs
    short_mult = 2.0 / 5.0
    long_mult = 2.0 / 25.0

    short_ema = closes[idx - 48]
    long_ema = closes[idx - 48]
    prev_short = short_ema
    prev_long = long_ema

    for i in range(idx - 47, idx + 1):
        prev_short = short_ema
        prev_long = long_ema
        short_ema = closes[i] * short_mult + short_ema * (1.0 - short_mult)
        long_ema = closes[i] * long_mult + long_ema * (1.0 - long_mult)

    short_trend = 1.0 if short_ema > prev_short else -1.0
    long_trend = 1.0 if long_ema > prev_long else -1.0

    if short_trend > 0 and long_trend > 0:
        return 0.85  # Both bullish
    elif short_trend < 0 and long_trend < 0:
        return 0.15  # Both bearish
    elif short_trend > 0 and long_trend < 0:
        return 0.6   # Short bullish diverging from long
    else:
        return 0.4   # Short bearish diverging from long
