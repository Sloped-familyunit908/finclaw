"""
Factor: momentum_divergence
Description: Price making new low but momentum (ROC) isn't
Category: momentum
"""

FACTOR_NAME = "momentum_divergence"
FACTOR_DESC = "Bullish momentum divergence — price new low but ROC isn't"
FACTOR_CATEGORY = "momentum"


def compute(closes, highs, lows, volumes, idx):
    """Detect when price makes new low but 5-day ROC doesn't."""
    lookback = 20
    roc_period = 5
    if idx < lookback + roc_period:
        return 0.5

    half = lookback // 2

    # Price lows in first half vs second half
    price_first_low = min(lows[idx - lookback + 1:idx - half + 1])
    price_second_low = min(lows[idx - half + 1:idx + 1])

    # ROC at those points
    def calc_roc(i):
        if i < roc_period or closes[i - roc_period] <= 0:
            return 0.0
        return (closes[i] - closes[i - roc_period]) / closes[i - roc_period]

    # Find ROC at the low points
    roc_at_first_low = 0.0
    for i in range(idx - lookback + 1, idx - half + 1):
        if lows[i] == price_first_low:
            roc_at_first_low = calc_roc(i)
            break

    roc_at_second_low = 0.0
    for i in range(idx - half + 1, idx + 1):
        if lows[i] == price_second_low:
            roc_at_second_low = calc_roc(i)
            break

    # Bullish divergence: price lower low, ROC higher low
    if price_second_low < price_first_low and roc_at_second_low > roc_at_first_low:
        score = 0.8
    # Bearish divergence: price higher high, ROC lower high
    elif price_second_low > price_first_low and roc_at_second_low < roc_at_first_low:
        score = 0.3
    else:
        score = 0.5

    return max(0.0, min(1.0, score))
