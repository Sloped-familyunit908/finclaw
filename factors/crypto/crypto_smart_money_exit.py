"""
Factor: crypto_smart_money_exit
Description: Price up but volume declining 5+ bars — smart money exiting
Category: crypto
"""

FACTOR_NAME = "crypto_smart_money_exit"
FACTOR_DESC = "Price rising while volume declines for 5+ bars — smart money exiting"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Low = smart money exiting (bearish divergence)."""
    lookback = 8
    if idx < lookback:
        return 0.5

    # Check if price has been rising
    price_rising_count = 0
    vol_declining_count = 0

    for i in range(1, lookback):
        if closes[idx - lookback + i + 1] > closes[idx - lookback + i]:
            price_rising_count += 1
        if volumes[idx - lookback + i + 1] < volumes[idx - lookback + i]:
            vol_declining_count += 1

    # Need price rising AND volume declining for 5+ consecutive bars
    # Check consecutive declining volume from current bar backwards
    consec_vol_decline = 0
    for i in range(idx, idx - lookback, -1):
        if i < 1:
            break
        if volumes[i] < volumes[i - 1]:
            consec_vol_decline += 1
        else:
            break

    consec_price_rise = 0
    for i in range(idx, idx - lookback, -1):
        if i < 1:
            break
        if closes[i] > closes[i - 1]:
            consec_price_rise += 1
        else:
            break

    if consec_vol_decline >= 5 and consec_price_rise >= 5:
        # Strong smart money exit signal — bearish
        strength = min(consec_vol_decline / 8.0, 1.0)
        score = 0.5 - strength * 0.45
    elif consec_vol_decline >= 3 and consec_price_rise >= 3:
        strength = min(consec_vol_decline / 8.0, 1.0)
        score = 0.5 - strength * 0.25
    else:
        score = 0.5

    return max(0.0, min(1.0, score))
