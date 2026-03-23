"""
Factor: crypto_stoch_divergence
Description: Price trend vs stochastic direction divergence
Category: crypto
"""

FACTOR_NAME = "crypto_stoch_divergence"
FACTOR_DESC = "Price trend vs stochastic direction divergence"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. >0.5 = bullish divergence, <0.5 = bearish divergence."""
    lookback = 14
    compare = 12
    if idx < lookback + compare:
        return 0.5

    def calc_k(i):
        highest = max(highs[i - lookback:i])
        lowest = min(lows[i - lookback:i])
        r = highest - lowest
        if r <= 0:
            return 0.5
        return (closes[i - 1] - lowest) / r

    k_now = calc_k(idx)
    k_past = calc_k(idx - compare)

    if closes[idx - compare - 1] <= 0:
        return 0.5

    price_change = (closes[idx - 1] - closes[idx - compare - 1]) / closes[idx - compare - 1]
    stoch_change = k_now - k_past

    # Bullish divergence: price falling but stochastic rising
    if price_change < -0.01 and stoch_change > 0.1:
        return min(1.0, 0.5 + stoch_change)
    # Bearish divergence: price rising but stochastic falling
    elif price_change > 0.01 and stoch_change < -0.1:
        return max(0.0, 0.5 + stoch_change)

    return 0.5
