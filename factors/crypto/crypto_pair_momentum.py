"""
Factor: crypto_pair_momentum
Description: Price/MA24 ratio relative to dataset leader — pair momentum
Category: crypto
"""

FACTOR_NAME = "crypto_pair_momentum"
FACTOR_DESC = "Price/MA24 ratio as pair momentum indicator"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """
    Returns float in [0, 1].
    Measures price relative to its 24-bar MA as a momentum signal.
    High = price well above MA (momentum), Low = price below MA.
    """
    period = 24
    if idx < period:
        return 0.5

    # 24-bar simple MA
    ma24 = sum(closes[idx - period + 1:idx + 1]) / period

    if ma24 <= 0:
        return 0.5

    # Price/MA ratio
    ratio = closes[idx] / ma24

    # Also check 48-bar MA for longer-term context
    if idx >= 48:
        ma48 = sum(closes[idx - 47:idx + 1]) / 48
        if ma48 > 0:
            ratio_48 = closes[idx] / ma48
            # Combine short and long ratios
            combined_ratio = ratio * 0.6 + ratio_48 * 0.4
        else:
            combined_ratio = ratio
    else:
        combined_ratio = ratio

    # Map: ratio 0.95 → 0.0, ratio 1.0 → 0.5, ratio 1.05 → 1.0
    score = (combined_ratio - 0.95) / 0.1

    return max(0.0, min(1.0, score))
