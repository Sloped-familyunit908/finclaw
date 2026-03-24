"""
Factor: breadth_market_momentum
Description: Average momentum proxy from price data
Category: market_breadth
"""

FACTOR_NAME = "breadth_market_momentum"
FACTOR_DESC = "Market-level momentum — average momentum proxy for strategy regime"
FACTOR_CATEGORY = "market_breadth"


def compute(closes, highs, lows, volumes, idx):
    """Market momentum proxy: combine multiple timeframe returns
    to estimate the overall market momentum regime.
    Strong positive momentum = momentum strategies work better.
    """
    if idx < 20:
        return 0.5

    # Multi-timeframe returns
    returns = []

    # 5-day return
    if closes[idx - 5] > 0:
        r5 = (closes[idx] - closes[idx - 5]) / closes[idx - 5]
        returns.append(r5)

    # 10-day return
    if idx >= 10 and closes[idx - 10] > 0:
        r10 = (closes[idx] - closes[idx - 10]) / closes[idx - 10]
        returns.append(r10)

    # 20-day return
    if closes[idx - 20] > 0:
        r20 = (closes[idx] - closes[idx - 20]) / closes[idx - 20]
        returns.append(r20)

    if not returns:
        return 0.5

    # Average return across timeframes
    avg_return = sum(returns) / len(returns)

    # Map to [0, 1]: -10% → 0, 0% → 0.5, +10% → 1.0
    score = 0.5 + avg_return * 5.0

    return max(0.0, min(1.0, score))
