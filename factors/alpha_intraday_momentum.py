FACTOR_NAME = "alpha_intraday_momentum"
FACTOR_DESC = "Sum of (close - open) over last 5 days / sum of (high - low) — intraday momentum"
FACTOR_CATEGORY = "alpha101"
LOOKBACK = 5

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    # Approximate open as previous close
    sum_co = 0.0
    sum_hl = 0.0
    for i in range(idx - LOOKBACK + 1, idx + 1):
        opn = closes[i - 1] if i > 0 else closes[i]
        sum_co += closes[i] - opn
        sum_hl += highs[i] - lows[i]
    if sum_hl == 0:
        return 0.5
    ratio = sum_co / sum_hl  # [-1, 1]
    score = 0.5 + ratio * 0.5
    return max(0.0, min(1.0, score))
