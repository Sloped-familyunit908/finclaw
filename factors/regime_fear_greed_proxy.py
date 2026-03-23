"""
Factor: fear_greed_proxy
Description: VIX-like volatility regime from price data — contrarian signal
Category: sentiment
"""

FACTOR_NAME = "fear_greed_proxy"
FACTOR_DESC = "Fear/greed proxy — realized volatility regime as contrarian buy signal"
FACTOR_CATEGORY = "sentiment"


def compute(closes, highs, lows, volumes, idx):
    """
    Fear/greed proxy based on rolling 20-day realized volatility.
    
    Low vol regime (< 15% annualized) = greed/complacency = score 0.0
    Medium vol (15-30%) = neutral = score 0.5
    High vol (> 30%) = fear/panic = score 1.0 (contrarian buy)
    
    Annualized volatility = daily_vol * sqrt(252)
    """
    vol_window = 20

    if idx < vol_window:
        return 0.5

    # Compute daily log returns
    returns = []
    for i in range(idx - vol_window + 1, idx + 1):
        if i < 1 or closes[i - 1] <= 0 or closes[i] <= 0:
            continue
        daily_ret = (closes[i] - closes[i - 1]) / closes[i - 1]
        returns.append(daily_ret)

    if len(returns) < 5:
        return 0.5

    # Mean return
    mean_ret = sum(returns) / len(returns)

    # Variance
    variance = 0.0
    for r in returns:
        variance += (r - mean_ret) ** 2
    variance /= len(returns)

    # Daily volatility -> annualized
    daily_vol = variance ** 0.5
    annual_vol = daily_vol * (252 ** 0.5)

    # Map: 15% -> 0.0, 30% -> 1.0 (contrarian)
    # Below 15% = greed (score 0.0)
    # Above 30% = fear (score 1.0 = contrarian buy)
    if annual_vol <= 0.15:
        score = 0.0
    elif annual_vol >= 0.30:
        score = 1.0
    else:
        score = (annual_vol - 0.15) / 0.15

    return max(0.0, min(1.0, score))
