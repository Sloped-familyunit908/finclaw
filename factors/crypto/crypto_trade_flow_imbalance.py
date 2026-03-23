"""
Factor: crypto_trade_flow_imbalance
Description: Close position in high-low range — buy/sell pressure proxy
Category: crypto
"""

FACTOR_NAME = "crypto_trade_flow_imbalance"
FACTOR_DESC = "Close position in high-low range as buy/sell pressure proxy"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = buying pressure, Low = selling pressure."""
    lookback = 12
    if idx < lookback:
        return 0.5

    # Rolling average of close position in range
    positions = []
    for i in range(idx - lookback + 1, idx + 1):
        bar_range = highs[i] - lows[i]
        if bar_range > 0:
            pos = (closes[i] - lows[i]) / bar_range
            positions.append(pos)

    if not positions:
        return 0.5

    avg_pos = sum(positions) / len(positions)

    # Weight recent bars more
    recent_pos = positions[-3:] if len(positions) >= 3 else positions
    recent_avg = sum(recent_pos) / len(recent_pos)

    # Blend: 60% recent, 40% overall
    score = 0.6 * recent_avg + 0.4 * avg_pos

    return max(0.0, min(1.0, score))
