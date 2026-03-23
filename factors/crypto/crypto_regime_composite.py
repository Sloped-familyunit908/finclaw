"""
Factor: crypto_regime_composite
Description: Weighted combo of trend/vol/mean-revert regime indicators
Category: crypto
"""

FACTOR_NAME = "crypto_regime_composite"
FACTOR_DESC = "Weighted combo of trend/vol/mean-revert regime indicators"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. >0.5 = trending regime favored, <0.5 = range/reversion."""
    if idx < 170:
        return 0.5

    # Trend strength via R-squared
    lookback = 24
    prices = closes[idx - lookback:idx]
    n = len(prices)
    mean_x = (n - 1) / 2.0
    mean_y = sum(prices) / n
    ss_xy = ss_xx = ss_yy = 0.0
    for i in range(n):
        dx = i - mean_x
        dy = prices[i] - mean_y
        ss_xy += dx * dy
        ss_xx += dx * dx
        ss_yy += dy * dy
    r_sq = (ss_xy ** 2) / (ss_xx * ss_yy) if ss_xx > 0 and ss_yy > 0 else 0.5

    # Volatility regime
    def calc_vol(start, end):
        rets = []
        for i in range(start, end):
            if i < 1 or closes[i - 1] <= 0:
                continue
            rets.append((closes[i] - closes[i - 1]) / closes[i - 1])
        if len(rets) < 2:
            return 0
        m = sum(rets) / len(rets)
        return (sum((r - m) ** 2 for r in rets) / len(rets)) ** 0.5

    sv = calc_vol(idx - 24, idx)
    lv = calc_vol(idx - 168, idx)
    vol_regime = 0.5 + (sv / lv - 1.0) * 0.3 if lv > 0 else 0.5
    vol_regime = max(0.0, min(1.0, vol_regime))

    # Weighted composite
    score = r_sq * 0.5 + vol_regime * 0.3 + 0.5 * 0.2
    return max(0.0, min(1.0, score))
