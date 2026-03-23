"""
Factor: crypto_mean_reversion_score
Description: Multi-indicator mean reversion signal
Category: crypto
"""

FACTOR_NAME = "crypto_mean_reversion_score"
FACTOR_DESC = "Multi-indicator mean reversion signal"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. >0.5 = oversold (buy reversion), <0.5 = overbought (sell)."""
    if idx < 50:
        return 0.5

    score = 0.0
    count = 0

    # 1. RSI extreme
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
    # Invert: low RSI -> high score (oversold = buy)
    score += (1.0 - rsi)
    count += 1

    # 2. Bollinger band position
    sma = sum(closes[idx - 20:idx]) / 20
    var = sum((closes[i] - sma) ** 2 for i in range(idx - 20, idx)) / 20
    std = var ** 0.5
    if std > 0:
        z = (closes[idx - 1] - sma) / (2 * std)
        bb_score = 0.5 - z * 0.5  # Below band = high score
        score += max(0.0, min(1.0, bb_score))
        count += 1

    # 3. Distance from VWAP
    cum_pv = cum_v = 0.0
    for i in range(idx - 24, idx):
        tp = (highs[i] + lows[i] + closes[i]) / 3.0
        cum_pv += tp * volumes[i]
        cum_v += volumes[i]
    if cum_v > 0:
        vwap = cum_pv / cum_v
        if vwap > 0:
            dist = (closes[idx - 1] - vwap) / vwap
            vwap_score = 0.5 - dist * 10.0
            score += max(0.0, min(1.0, vwap_score))
            count += 1

    if count <= 0:
        return 0.5

    return max(0.0, min(1.0, score / count))
