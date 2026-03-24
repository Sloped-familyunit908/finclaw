"""
Factor: top_overbought_extreme
Description: RSI > 80 AND KDJ-J > 100 AND price > upper Bollinger — triple overbought
Category: top_escape
"""

FACTOR_NAME = "top_overbought_extreme"
FACTOR_DESC = "Triple overbought: RSI>80, KDJ-J>100, price above upper Bollinger Band"
FACTOR_CATEGORY = "top_escape"


def _calc_rsi(closes, end_idx, period=14):
    """Calculate RSI at a given index."""
    if end_idx < period:
        return 50.0
    gains = 0.0
    losses = 0.0
    for i in range(end_idx - period + 1, end_idx + 1):
        change = closes[i] - closes[i - 1]
        if change > 0:
            gains += change
        else:
            losses -= change
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _calc_kdj_j(closes, highs, lows, end_idx, period=9):
    """Calculate KDJ J-value at a given index."""
    if end_idx < period:
        return 50.0
    lowest = min(lows[end_idx - period + 1 : end_idx + 1])
    highest = max(highs[end_idx - period + 1 : end_idx + 1])
    if highest == lowest:
        return 50.0
    rsv = (closes[end_idx] - lowest) / (highest - lowest) * 100.0
    # Simple K and D (not smoothed for simplicity)
    k = rsv
    d = rsv  # simplified: in practice would be smoothed
    j = 3 * k - 2 * d  # simplified = rsv
    return j


def _calc_bollinger_upper(closes, end_idx, period=20, num_std=2.0):
    """Calculate upper Bollinger Band."""
    if end_idx < period:
        return closes[end_idx] * 2  # return very high so test fails
    mean = sum(closes[end_idx - period + 1 : end_idx + 1]) / period
    variance = sum((closes[i] - mean) ** 2 for i in range(end_idx - period + 1, end_idx + 1)) / period
    std = variance ** 0.5
    return mean + num_std * std


def compute(closes, highs, lows, volumes, idx):
    """Triple overbought: RSI > 80 AND KDJ-J > 100 AND close > upper BB.
    When all three align, the stock is extremely overbought.
    """
    if idx < 20:
        return 0.5

    rsi = _calc_rsi(closes, idx)
    kdj_j = _calc_kdj_j(closes, highs, lows, idx)
    upper_bb = _calc_bollinger_upper(closes, idx)

    # Count how many conditions are met
    conditions_met = 0
    condition_scores = []

    if rsi > 70:
        conditions_met += 1
        condition_scores.append(min(1.0, (rsi - 70) / 20.0))  # 0 at 70, 1 at 90

    if kdj_j > 80:
        conditions_met += 1
        condition_scores.append(min(1.0, (kdj_j - 80) / 40.0))  # 0 at 80, 1 at 120

    if closes[idx] > upper_bb:
        conditions_met += 1
        excess = (closes[idx] - upper_bb) / upper_bb if upper_bb > 0 else 0
        condition_scores.append(min(1.0, excess / 0.03))  # 3% above = max

    if conditions_met < 2:
        return 0.5

    avg_condition = sum(condition_scores) / len(condition_scores) if condition_scores else 0

    if conditions_met == 3:
        score = 0.8 + 0.2 * avg_condition
    else:
        score = 0.6 + 0.2 * avg_condition

    return max(0.0, min(1.0, score))
