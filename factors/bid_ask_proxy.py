"""
Auto-generated factor: bid_ask_proxy
Description: (High - Low) / Volume as proxy for spread/liquidity
Category: microstructure
Generated: seed
"""

FACTOR_NAME = "bid_ask_proxy"
FACTOR_DESC = "(High - Low) / Volume as proxy for spread/liquidity"
FACTOR_CATEGORY = "microstructure"


def compute(closes, highs, lows, volumes, idx):
    """Bid-ask spread proxy: range / volume. Lower = more liquid = better."""

    lookback = 5
    if idx < lookback:
        return 0.5

    # Average spread proxy over last 5 days for stability
    total_spread = 0.0
    valid = 0
    for i in range(idx - lookback + 1, idx + 1):
        if volumes[i] > 0:
            spread = (highs[i] - lows[i]) / volumes[i]
            total_spread += spread
            valid += 1

    if valid == 0:
        return 0.5

    avg_spread = total_spread / valid

    # Compare to 20-day average spread
    if idx < 20:
        return 0.5

    long_total = 0.0
    long_valid = 0
    for i in range(idx - 19, idx + 1):
        if volumes[i] > 0:
            s = (highs[i] - lows[i]) / volumes[i]
            long_total += s
            long_valid += 1

    if long_valid == 0:
        return 0.5

    long_avg = long_total / long_valid

    if long_avg < 1e-20:
        return 0.5

    # Lower spread = more liquid = bullish
    ratio = avg_spread / long_avg
    score = 1.0 - ratio * 0.5
    return max(0.0, min(1.0, score))
