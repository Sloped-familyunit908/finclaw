FACTOR_NAME = "tail_ratio"
FACTOR_DESC = "95th percentile return / abs(5th percentile return) — tail asymmetry"
FACTOR_CATEGORY = "statistical"
LOOKBACK = 60

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    rets = []
    for i in range(idx - LOOKBACK + 1, idx + 1):
        if i > 0 and closes[i - 1] != 0:
            rets.append((closes[i] - closes[i - 1]) / closes[i - 1])
    if len(rets) < 10:
        return 0.5
    # Sort to find percentiles
    sorted_rets = sorted(rets)
    n = len(sorted_rets)
    # 5th percentile index
    idx_5 = max(0, int(n * 0.05))
    # 95th percentile index
    idx_95 = min(n - 1, int(n * 0.95))
    p5 = sorted_rets[idx_5]
    p95 = sorted_rets[idx_95]
    if abs(p5) < 1e-8:
        return 0.5
    tail_r = p95 / abs(p5)
    # tail_ratio > 1 = upside tail bigger than downside = bullish
    # Map [0, 3] to [0, 1]
    score = tail_r / 3.0
    return max(0.0, min(1.0, score))
