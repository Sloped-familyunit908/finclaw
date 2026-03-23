"""
Factor: crypto_consecutive_candles
Description: Count of consecutive green/red candles — 5+ same-color signals exhaustion
Category: crypto
"""

FACTOR_NAME = "crypto_consecutive_candles"
FACTOR_DESC = "Consecutive candle exhaustion — 5+ same-color 1h candles often signal reversal in crypto"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """
    Counts consecutive green (close > open proxy) or red candles.
    In crypto, 5+ consecutive same-direction candles often signal exhaustion.
    
    Many consecutive green → overbought, expect pullback → bearish
    Many consecutive red → oversold, expect bounce → bullish
    Few consecutive → neutral
    
    Uses close > prev_close as green/red proxy since we don't have open.
    """
    if idx < 1:
        return 0.5

    # Count consecutive up or down
    consecutive_up = 0
    consecutive_down = 0

    # Count consecutive green candles going backwards
    for i in range(idx, 0, -1):
        if closes[i] > closes[i - 1]:
            consecutive_up += 1
        else:
            break

    # If no consecutive up, count consecutive red
    if consecutive_up == 0:
        for i in range(idx, 0, -1):
            if closes[i] < closes[i - 1]:
                consecutive_down += 1
            else:
                break

    # Exhaustion logic (mean reversion bias)
    if consecutive_up >= 7:
        score = 0.15  # Very overbought, strong reversal expected
    elif consecutive_up >= 5:
        score = 0.25  # Overbought
    elif consecutive_up >= 3:
        score = 0.40  # Mildly overbought
    elif consecutive_down >= 7:
        score = 0.85  # Very oversold, strong bounce expected
    elif consecutive_down >= 5:
        score = 0.75  # Oversold
    elif consecutive_down >= 3:
        score = 0.60  # Mildly oversold
    else:
        score = 0.50  # Neutral

    return score
