"""
Factor: crypto_bear_power_composite
Description: Combines: RSI<50 + MACD<0 + price<EMA24 + vol>avg (bearish)
Category: crypto
"""

FACTOR_NAME = "crypto_bear_power_composite"
FACTOR_DESC = "Combines: RSI<50 + MACD<0 + price<EMA24 + vol>avg (bearish)"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = multiple bearish signals aligned."""
    if idx < 50:
        return 0.5

    signals = 0
    total = 4

    # 1. RSI < 50
    period = 14
    gains = losses = 0.0
    for i in range(idx - period, idx):
        if i < 1:
            continue
        c = closes[i] - closes[i - 1]
        if c > 0:
            gains += c
        else:
            losses += abs(c)
    rsi = gains / (gains + losses) if (gains + losses) > 0 else 0.5
    if rsi < 0.5:
        signals += 1

    # 2. MACD < 0
    def calc_ema(data, start, end, p):
        m = 2.0 / (p + 1)
        e = data[start]
        for i in range(start + 1, end):
            e = data[i] * m + e * (1 - m)
        return e

    ema12 = calc_ema(closes, idx - 26, idx, 12)
    ema26 = calc_ema(closes, idx - 26, idx, 26)
    if ema12 < ema26:
        signals += 1

    # 3. Price < EMA24
    ema24 = calc_ema(closes, idx - 24, idx, 24)
    if closes[idx - 1] < ema24:
        signals += 1

    # 4. Volume > average (high vol on down move)
    avg_vol = sum(volumes[idx - 24:idx]) / 24
    if volumes[idx - 1] > avg_vol:
        signals += 1

    score = signals / total
    return max(0.0, min(1.0, score))
