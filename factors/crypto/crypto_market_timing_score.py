"""
Factor: crypto_market_timing_score
Description: Composite: volatility regime + trend + momentum + volume
Category: crypto
"""

FACTOR_NAME = "crypto_market_timing_score"
FACTOR_DESC = "Composite: volatility regime + trend + momentum + volume"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. >0.5 = favorable market timing, <0.5 = unfavorable."""
    if idx < 50:
        return 0.5

    score = 0.0

    # 1. Trend: price vs SMA20 (0.25)
    sma = sum(closes[idx - 20:idx]) / 20
    if sma > 0:
        trend = 1.0 if closes[idx - 1] > sma else 0.0
        score += trend * 0.25

    # 2. Momentum: 12-bar return (0.25)
    if closes[idx - 13] > 0:
        mom_ret = (closes[idx - 1] - closes[idx - 13]) / closes[idx - 13]
        mom = 0.5 + mom_ret * 10.0
        score += max(0.0, min(1.0, mom)) * 0.25

    # 3. Volatility regime: recent vs long-term (0.25)
    def calc_std(start, end):
        rets = []
        for i in range(start, end):
            if i < 1 or closes[i - 1] <= 0:
                continue
            rets.append((closes[i] - closes[i - 1]) / closes[i - 1])
        if len(rets) < 2:
            return 0
        m = sum(rets) / len(rets)
        return (sum((r - m) ** 2 for r in rets) / len(rets)) ** 0.5

    sv = calc_std(idx - 12, idx)
    lv = calc_std(idx - 48, idx)
    # Lower recent vol relative to long-term = favorable
    vol_score = 0.5 + (1.0 - sv / lv) * 0.3 if lv > 0 else 0.5
    score += max(0.0, min(1.0, vol_score)) * 0.25

    # 4. Volume confirmation (0.25)
    avg_vol = sum(volumes[idx - 24:idx]) / 24
    if avg_vol > 0:
        vol_ratio = volumes[idx - 1] / avg_vol
        if closes[idx - 1] > closes[idx - 2] if idx > 1 else False:
            v = min(vol_ratio / 2.0, 1.0)
        else:
            v = max(0.0, 1.0 - vol_ratio / 2.0)
        score += v * 0.25

    return max(0.0, min(1.0, score))
