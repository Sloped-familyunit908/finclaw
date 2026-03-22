FACTOR_NAME = "hurst_exponent"
FACTOR_DESC = "Simplified Hurst exponent proxy via R/S analysis — H>0.5 trending, H<0.5 mean-reverting"
FACTOR_CATEGORY = "statistical"
LOOKBACK = 30

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    # Compute returns
    rets = []
    for i in range(idx - LOOKBACK + 1, idx + 1):
        if i > 0 and closes[i - 1] != 0:
            rets.append((closes[i] - closes[i - 1]) / closes[i - 1])
    if len(rets) < 10:
        return 0.5
    n = len(rets)
    mean_r = sum(rets) / n
    # Cumulative deviations
    cum_dev = []
    running = 0.0
    for r in rets:
        running += r - mean_r
        cum_dev.append(running)
    R = max(cum_dev) - min(cum_dev)
    # Standard deviation
    var = sum((r - mean_r) ** 2 for r in rets) / n
    S = var ** 0.5
    if S == 0:
        return 0.5
    RS = R / S
    # H = log(R/S) / log(n) — simplified
    if RS <= 0 or n <= 1:
        return 0.5
    # Use log approximation: log(x) ≈ iterative
    # Simple: ln(x) via series isn't practical, use ratio approach
    # H ≈ RS / n^0.5 normalized
    # For 30 data points, expected RS for random walk ≈ sqrt(n*pi/2) ≈ 6.86
    expected_rs = (n * 3.14159 / 2.0) ** 0.5
    h_proxy = RS / expected_rs  # >1 = trending, <1 = mean-reverting
    # If price is trending up and H > 0.5, bullish (trend continues)
    # If mean-reverting and price is down, also bullish (will revert up)
    price_trend = (closes[idx] - closes[idx - LOOKBACK + 1]) / closes[idx - LOOKBACK + 1] if closes[idx - LOOKBACK + 1] != 0 else 0
    if h_proxy > 1.0 and price_trend > 0:
        score = 0.5 + min(h_proxy - 1.0, 0.5)  # Trending up
    elif h_proxy < 1.0 and price_trend < 0:
        score = 0.5 + min(1.0 - h_proxy, 0.5)  # Mean-reverting from down
    elif h_proxy > 1.0 and price_trend < 0:
        score = 0.5 - min(h_proxy - 1.0, 0.5)  # Trending down
    else:
        score = 0.5
    return max(0.0, min(1.0, score))
