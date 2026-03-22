FACTOR_NAME = "chaikin_volatility"
FACTOR_DESC = "Rate of change of 10-day EMA of (high-low) — Chaikin Volatility"
FACTOR_CATEGORY = "price_structure"
LOOKBACK = 20

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    mult = 2.0 / 11.0
    # EMA of (high-low) ending at idx
    ema_now = highs[idx - LOOKBACK + 1] - lows[idx - LOOKBACK + 1]
    for i in range(idx - LOOKBACK + 2, idx + 1):
        hl = highs[i] - lows[i]
        ema_now = (hl - ema_now) * mult + ema_now
    # EMA of (high-low) ending at idx-10
    ema_prev = highs[idx - LOOKBACK + 1] - lows[idx - LOOKBACK + 1]
    for i in range(idx - LOOKBACK + 2, idx - 10 + 1):
        hl = highs[i] - lows[i]
        ema_prev = (hl - ema_prev) * mult + ema_prev
    if ema_prev == 0:
        return 0.5
    roc = (ema_now - ema_prev) / ema_prev
    # Decreasing volatility (negative ROC) after selloff can be bullish
    # Map [-0.5, 0.5] to [0, 1], inverted (decreasing vol = bullish)
    score = 0.5 - roc
    return max(0.0, min(1.0, score))
