"""
Factor: crypto_reversal_score
Description: Composite: RSI extreme + volume spike + candle pattern
Category: crypto
"""

FACTOR_NAME = "crypto_reversal_score"
FACTOR_DESC = "Composite reversal score: RSI + volume + candle pattern"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Near 1 = bullish reversal likely, near 0 = bearish reversal likely."""
    if idx < 25:
        return 0.5

    # Component 1: RSI extremity
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
    else:
        rsi = 50.0

    # RSI extreme: below 30 = bullish reversal, above 70 = bearish reversal
    if rsi < 30:
        rsi_signal = 0.5 + (30 - rsi) / 60.0
    elif rsi > 70:
        rsi_signal = 0.5 - (rsi - 70) / 60.0
    else:
        rsi_signal = 0.5

    # Component 2: Volume spike
    avg_vol = sum(volumes[idx - 24:idx]) / 24
    vol_spike = volumes[idx] / avg_vol if avg_vol > 0 else 1.0
    vol_signal = min(vol_spike / 3.0, 1.0) * 0.3 + 0.35  # Higher volume = more reversal signal

    # Component 3: Candle pattern (hammer/doji)
    body = abs(closes[idx] - closes[idx - 1]) if idx > 0 else 0
    hl_range = highs[idx] - lows[idx]
    if hl_range > 0:
        body_ratio = body / hl_range
        # Small body with long wick = reversal candle
        candle_signal = 1.0 - body_ratio
    else:
        candle_signal = 0.5

    score = rsi_signal * 0.5 + vol_signal * 0.25 + candle_signal * 0.25
    return max(0.0, min(1.0, score))
