"""
Factor: crypto_mfi_14
Description: Money Flow Index (14 period, volume-weighted RSI)
Category: crypto
"""

FACTOR_NAME = "crypto_mfi_14"
FACTOR_DESC = "Money Flow Index (14 period)"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Maps MFI 0-100 to 0.0-1.0."""
    period = 14
    if idx < period + 1:
        return 0.5

    positive_flow = 0.0
    negative_flow = 0.0

    for i in range(idx - period + 1, idx + 1):
        typical_price = (highs[i] + lows[i] + closes[i]) / 3.0
        prev_typical = (highs[i - 1] + lows[i - 1] + closes[i - 1]) / 3.0
        raw_money_flow = typical_price * volumes[i]

        if typical_price > prev_typical:
            positive_flow += raw_money_flow
        elif typical_price < prev_typical:
            negative_flow += raw_money_flow

    if negative_flow == 0:
        return 1.0
    if positive_flow == 0:
        return 0.0

    money_ratio = positive_flow / negative_flow
    mfi = 100 - (100 / (1 + money_ratio))

    return max(0.0, min(1.0, mfi / 100.0))
