FACTOR_NAME = "alpha_return_reversal"
FACTOR_DESC = "Short-term reversal alpha: -1 x 5-day return"
FACTOR_CATEGORY = "alpha101"
LOOKBACK = 5

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    if closes[idx - 5] == 0:
        return 0.5
    ret_5d = (closes[idx] - closes[idx - 5]) / closes[idx - 5]
    reversal = -ret_5d
    # Map from roughly [-0.1, 0.1] to [0, 1]
    score = 0.5 + reversal * 5.0
    return max(0.0, min(1.0, score))
