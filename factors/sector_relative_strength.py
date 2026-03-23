"""
Factor: relative_strength_vs_market
Description: Stock's 20-day return vs market average return
Category: rotation
"""

FACTOR_NAME = "relative_strength_vs_market"
FACTOR_DESC = "Relative strength vs market — stock 20-day return vs market average"
FACTOR_CATEGORY = "rotation"


def compute(closes, highs, lows, volumes, idx):
    """
    Relative strength vs market proxy.
    
    Since we only have single-stock data in this compute call,
    we compare the stock's 20-day return against a "market proxy"
    derived from the stock's own long-term average return.
    
    >0.5 = outperforming its own trend (bullish)
    <0.5 = underperforming its own trend (bearish)
    """
    short_window = 20
    long_window = 60

    if idx < long_window:
        return 0.5

    # Stock's 20-day return
    if closes[idx - short_window] <= 0:
        return 0.5
    ret_20d = (closes[idx] - closes[idx - short_window]) / closes[idx - short_window]

    # Long-term "market proxy": 60-day average daily return * 20
    # This approximates average 20-day return over the longer period
    daily_returns = []
    for i in range(idx - long_window + 1, idx + 1):
        if i < 1 or closes[i - 1] <= 0:
            continue
        daily_returns.append((closes[i] - closes[i - 1]) / closes[i - 1])

    if len(daily_returns) == 0:
        return 0.5

    avg_daily_ret = sum(daily_returns) / len(daily_returns)
    expected_20d_ret = avg_daily_ret * short_window

    # Relative strength = actual vs expected
    excess_return = ret_20d - expected_20d_ret

    # Normalize: +-10% excess return maps to [0, 1]
    score = 0.5 + excess_return / 0.2

    return max(0.0, min(1.0, score))
