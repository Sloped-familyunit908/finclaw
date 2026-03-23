"""
Factor: crypto_large_move_reversal
Description: After >5% move in 4 hours, probability of reversal is high
Category: crypto
"""

FACTOR_NAME = "crypto_large_move_reversal"
FACTOR_DESC = "Large move reversal — after >5% move in 4h, crypto tends to mean-revert"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """
    Measures the magnitude of the price move over the last 4 bars (4h for 1h data).
    Large down moves (>5%) → bullish reversal signal (score > 0.5)
    Large up moves (>5%) → bearish reversal signal (score < 0.5)
    No significant move → neutral (0.5)
    """
    lookback = 4
    if idx < lookback:
        return 0.5

    price_then = closes[idx - lookback]
    if price_then <= 0:
        return 0.5

    move_pct = (closes[idx] - price_then) / price_then

    # Reversal logic: big down = expect bounce (bullish), big up = expect pullback (bearish)
    if abs(move_pct) < 0.02:
        return 0.5  # No significant move

    # -10% move -> score 1.0 (strong reversal expected)
    # +10% move -> score 0.0 (pullback expected)
    # 0% -> 0.5
    score = 0.5 - move_pct * 5.0  # 5% move maps to full range
    return max(0.0, min(1.0, score))
