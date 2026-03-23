"""
Factor: crypto_engulfing_signal
Description: Bullish/bearish engulfing pattern at key levels
Category: crypto
"""

FACTOR_NAME = "crypto_engulfing_signal"
FACTOR_DESC = "Engulfing candlestick pattern — strong reversal signal"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = bullish engulfing, Low = bearish engulfing."""
    if idx < 24:
        return 0.5

    # Current and previous candle bodies
    open_curr = closes[idx - 1]
    open_prev = closes[idx - 2] if idx >= 2 else closes[idx - 1]

    body_curr = closes[idx] - open_curr
    body_prev = closes[idx - 1] - open_prev

    curr_size = abs(body_curr)
    prev_size = abs(body_prev)

    if prev_size <= 0:
        return 0.5

    # Bullish engulfing: prev was bearish (red), current is bullish (green) and larger
    if body_prev < 0 and body_curr > 0 and curr_size > prev_size:
        # Check if near recent low
        low_24h = min(lows[idx - 24:idx])
        if low_24h > 0 and (lows[idx - 1] - low_24h) / low_24h < 0.02:
            strength = min(curr_size / prev_size / 3.0, 1.0)
            return max(0.0, min(1.0, 0.5 + strength * 0.4))
        return 0.6

    # Bearish engulfing: prev was bullish, current is bearish and larger
    if body_prev > 0 and body_curr < 0 and curr_size > prev_size:
        high_24h = max(highs[idx - 24:idx])
        if high_24h > 0 and (high_24h - highs[idx - 1]) / high_24h < 0.02:
            strength = min(curr_size / prev_size / 3.0, 1.0)
            return max(0.0, min(1.0, 0.5 - strength * 0.4))
        return 0.4

    return 0.5
