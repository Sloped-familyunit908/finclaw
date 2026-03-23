"""
Factor: crypto_signal_confluence
Description: Count of how many simple signals agree (majority vote)
Category: crypto
"""

FACTOR_NAME = "crypto_signal_confluence"
FACTOR_DESC = "Signal confluence: count of agreeing bullish/bearish indicators"
FACTOR_CATEGORY = "crypto"


def _ema(data, period, end_idx):
    """Compute EMA ending at end_idx."""
    if end_idx < period:
        return sum(data[:end_idx + 1]) / (end_idx + 1) if end_idx >= 0 else 0
    k = 2.0 / (period + 1)
    start = end_idx - period * 3
    if start < 0:
        start = 0
    val = sum(data[start:start + period]) / period
    for i in range(start + period, end_idx + 1):
        val = data[i] * k + val * (1 - k)
    return val


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Above 0.5 = more bullish signals, below = more bearish."""
    if idx < 48:
        return 0.5

    bullish = 0
    bearish = 0
    total = 0

    # Signal 1: Price above EMA24
    ema24 = _ema(closes, 24, idx)
    total += 1
    if closes[idx] > ema24:
        bullish += 1
    else:
        bearish += 1

    # Signal 2: EMA12 > EMA24
    ema12 = _ema(closes, 12, idx)
    total += 1
    if ema12 > ema24:
        bullish += 1
    else:
        bearish += 1

    # Signal 3: RSI above 50
    period = 14
    if idx >= period + 1:
        gains = 0.0
        losses = 0.0
        for i in range(idx - period, idx):
            change = closes[i + 1] - closes[i]
            if change > 0:
                gains += change
            else:
                losses += abs(change)
        if losses == 0:
            rsi = 100.0
        elif gains == 0:
            rsi = 0.0
        else:
            rs = (gains / period) / (losses / period)
            rsi = 100 - (100 / (1 + rs))
        total += 1
        if rsi > 50:
            bullish += 1
        else:
            bearish += 1

    # Signal 4: Positive momentum (12-bar)
    if closes[idx - 12] > 0:
        mom = (closes[idx] - closes[idx - 12]) / closes[idx - 12]
        total += 1
        if mom > 0:
            bullish += 1
        else:
            bearish += 1

    # Signal 5: Volume above average
    avg_vol = sum(volumes[idx - 24:idx]) / 24
    total += 1
    if volumes[idx] > avg_vol:
        bullish += 1
    else:
        bearish += 1

    # Signal 6: Higher high
    total += 1
    if highs[idx] > highs[idx - 1]:
        bullish += 1
    else:
        bearish += 1

    if total == 0:
        return 0.5

    score = bullish / total
    return max(0.0, min(1.0, score))
