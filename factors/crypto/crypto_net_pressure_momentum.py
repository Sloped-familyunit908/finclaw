"""
Factor: crypto_net_pressure_momentum
Description: Rate of change of buying pressure — momentum of order flow
Category: crypto
"""

FACTOR_NAME = "crypto_net_pressure_momentum"
FACTOR_DESC = "Rate of change of buying pressure over recent bars"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = buying pressure accelerating."""
    lookback = 24
    if idx < lookback:
        return 0.5

    def buying_pressure(start, end):
        total = 0.0
        count = 0
        for i in range(start, end):
            rng = highs[i] - lows[i]
            if rng > 0:
                total += (closes[i] - lows[i]) / rng
                count += 1
        return total / count if count > 0 else 0.5

    recent = buying_pressure(idx - 6, idx)
    earlier = buying_pressure(idx - 12, idx - 6)

    momentum = recent - earlier  # Range roughly [-1, 1]
    score = 0.5 + momentum * 0.5
    return max(0.0, min(1.0, score))
