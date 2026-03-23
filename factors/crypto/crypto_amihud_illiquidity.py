"""
Factor: crypto_amihud_illiquidity
Description: |return|/volume — Amihud illiquidity measure
Category: crypto
"""

FACTOR_NAME = "crypto_amihud_illiquidity"
FACTOR_DESC = "Amihud illiquidity: |return|/volume — high values signal illiquid market"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = liquid market, Low = illiquid."""
    lookback = 24
    if idx < lookback:
        return 0.5

    # Compute rolling Amihud illiquidity
    illiq_values = []
    for i in range(idx - lookback + 1, idx + 1):
        if closes[i - 1] > 0 and volumes[i] > 0:
            abs_return = abs(closes[i] - closes[i - 1]) / closes[i - 1]
            illiq = abs_return / volumes[i]
            illiq_values.append(illiq)

    if len(illiq_values) < 5:
        return 0.5

    current_illiq = illiq_values[-1] if illiq_values else 0
    avg_illiq = sum(illiq_values) / len(illiq_values)

    if avg_illiq <= 0:
        return 0.5

    # Ratio: current illiquidity relative to average
    ratio = current_illiq / avg_illiq

    # High illiquidity (ratio > 1) is risky → low score
    # Low illiquidity (ratio < 1) is good → high score
    score = 1.0 - min(ratio / 4.0, 1.0)

    return max(0.0, min(1.0, score))
