"""
Factor: obv_divergence
Description: OBV making new high but price isn't (or vice versa)
Category: volume
"""

FACTOR_NAME = "obv_divergence"
FACTOR_DESC = "OBV divergence with price — OBV new high but price not (bullish)"
FACTOR_CATEGORY = "volume"


def compute(closes, highs, lows, volumes, idx):
    """On-Balance Volume divergence from price."""
    lookback = 20
    if idx < lookback + 1:
        return 0.5

    # Calculate OBV for recent period
    obv = [0.0] * (lookback + 1)
    start = idx - lookback
    obv[0] = 0.0
    for i in range(1, lookback + 1):
        pos = start + i
        if closes[pos] > closes[pos - 1]:
            obv[i] = obv[i - 1] + volumes[pos]
        elif closes[pos] < closes[pos - 1]:
            obv[i] = obv[i - 1] - volumes[pos]
        else:
            obv[i] = obv[i - 1]

    # Compare first half and second half for highs
    half = lookback // 2

    price_first_high = max(closes[start:start + half + 1])
    price_second_high = max(closes[start + half:idx + 1])
    obv_first_high = max(obv[:half + 1])
    obv_second_high = max(obv[half:])

    price_first_low = min(closes[start:start + half + 1])
    price_second_low = min(closes[start + half:idx + 1])
    obv_first_low = min(obv[:half + 1])
    obv_second_low = min(obv[half:])

    # Bullish divergence: price makes lower low but OBV makes higher low
    if price_second_low < price_first_low and obv_second_low > obv_first_low:
        return 0.8

    # Bullish: OBV makes new high ahead of price
    if obv_second_high > obv_first_high and price_second_high <= price_first_high:
        return 0.75

    # Bearish divergence: price makes higher high but OBV makes lower high
    if price_second_high > price_first_high and obv_second_high < obv_first_high:
        return 0.25

    # Bearish: OBV makes new low
    if obv_second_low < obv_first_low and price_second_low >= price_first_low:
        return 0.3

    return 0.5
