FACTOR_NAME = "alpha_close_to_high"
FACTOR_DESC = "close / rolling_max(close, 20) — how close to recent peak"
FACTOR_CATEGORY = "alpha101"
LOOKBACK = 20

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    max_close = closes[idx - LOOKBACK + 1]
    for i in range(idx - LOOKBACK + 1, idx + 1):
        if closes[i] > max_close:
            max_close = closes[i]
    if max_close == 0:
        return 0.5
    score = closes[idx] / max_close
    return max(0.0, min(1.0, score))
