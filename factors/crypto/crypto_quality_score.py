"""
Factor: crypto_quality_score
Description: Composite: trend consistency + volume confirmation + low vol
Category: crypto
"""

FACTOR_NAME = "crypto_quality_score"
FACTOR_DESC = "Composite quality score: consistency + volume + volatility"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Higher = higher quality trend (consistent + confirmed)."""
    lookback = 24
    if idx < lookback + 1:
        return 0.5

    # Component 1: Trend consistency (% bars moving in dominant direction)
    up_bars = 0
    down_bars = 0
    for i in range(idx - lookback, idx):
        if closes[i + 1] > closes[i]:
            up_bars += 1
        elif closes[i + 1] < closes[i]:
            down_bars += 1
    consistency = max(up_bars, down_bars) / lookback

    # Component 2: Volume confirmation (volume higher on trend-direction bars)
    trend_vol = 0.0
    counter_vol = 0.0
    is_uptrend = up_bars > down_bars
    for i in range(idx - lookback, idx):
        if is_uptrend and closes[i + 1] > closes[i]:
            trend_vol += volumes[i + 1]
        elif not is_uptrend and closes[i + 1] < closes[i]:
            trend_vol += volumes[i + 1]
        else:
            counter_vol += volumes[i + 1]

    total_vol = trend_vol + counter_vol
    vol_confirm = trend_vol / total_vol if total_vol > 0 else 0.5

    # Component 3: Low volatility (smooth trend = higher quality)
    returns = []
    for i in range(idx - lookback + 1, idx + 1):
        if closes[i - 1] > 0:
            returns.append(abs((closes[i] - closes[i - 1]) / closes[i - 1]))
    avg_abs_ret = sum(returns) / len(returns) if returns else 0
    # Lower vol = higher quality, typical range 0.1% to 3%
    smoothness = 1.0 - min(avg_abs_ret / 0.03, 1.0)

    score = consistency * 0.4 + vol_confirm * 0.35 + smoothness * 0.25
    return max(0.0, min(1.0, score))
