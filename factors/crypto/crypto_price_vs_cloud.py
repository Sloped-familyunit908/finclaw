"""
Factor: crypto_price_vs_cloud
Description: Price position relative to Ichimoku cloud
Category: crypto
"""

FACTOR_NAME = "crypto_price_vs_cloud"
FACTOR_DESC = "Price position relative to Ichimoku cloud"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. 1.0 = well above cloud, 0.0 = well below, 0.5 = inside."""
    if idx < 52:
        return 0.5

    # Senkou A = (tenkan + kijun) / 2
    tenkan_h = max(highs[idx - 9:idx])
    tenkan_l = min(lows[idx - 9:idx])
    tenkan = (tenkan_h + tenkan_l) / 2.0

    kijun_h = max(highs[idx - 26:idx])
    kijun_l = min(lows[idx - 26:idx])
    kijun = (kijun_h + kijun_l) / 2.0

    senkou_a = (tenkan + kijun) / 2.0

    # Senkou B = (highest_52 + lowest_52) / 2
    senkou_b_h = max(highs[idx - 52:idx])
    senkou_b_l = min(lows[idx - 52:idx])
    senkou_b = (senkou_b_h + senkou_b_l) / 2.0

    cloud_top = max(senkou_a, senkou_b)
    cloud_bot = min(senkou_a, senkou_b)
    cloud_width = cloud_top - cloud_bot

    price = closes[idx - 1]
    if cloud_width <= 0:
        return 0.5

    if price >= cloud_top:
        dist = (price - cloud_top) / cloud_width
        score = 0.5 + min(dist, 1.0) * 0.5
    elif price <= cloud_bot:
        dist = (cloud_bot - price) / cloud_width
        score = 0.5 - min(dist, 1.0) * 0.5
    else:
        position = (price - cloud_bot) / cloud_width
        score = 0.4 + position * 0.2

    return max(0.0, min(1.0, score))
