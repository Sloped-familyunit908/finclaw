"""
Factor: breadth_correlation_regime
Description: Stock correlation with market average proxy
Category: market_breadth
"""

FACTOR_NAME = "breadth_correlation_regime"
FACTOR_DESC = "Correlation with market proxy — high correlation = beta, no alpha"
FACTOR_CATEGORY = "market_breadth"


def compute(closes, highs, lows, volumes, idx):
    """Estimate how "correlated" the stock moves are with a smooth trend.
    High serial correlation in returns = trending (correlated regime).
    Low serial correlation = more idiosyncratic (decorrelated, alpha potential).

    Score high when stock is highly correlated (= just beta, no alpha).
    """
    period = 20
    if idx < period + 1:
        return 0.5

    # Calculate daily returns
    daily_returns = []
    for i in range(idx - period + 1, idx + 1):
        if closes[i - 1] > 0:
            daily_returns.append((closes[i] - closes[i - 1]) / closes[i - 1])
        else:
            daily_returns.append(0.0)

    if len(daily_returns) < 10:
        return 0.5

    # Serial correlation (lag-1 autocorrelation) as proxy for market correlation
    n = len(daily_returns)
    mean_r = sum(daily_returns) / n

    cov = 0.0
    var = 0.0
    for i in range(1, n):
        cov += (daily_returns[i] - mean_r) * (daily_returns[i - 1] - mean_r)
        var += (daily_returns[i] - mean_r) ** 2

    if var <= 0:
        return 0.5

    autocorr = cov / var

    # Map autocorrelation to [0, 1]
    # High positive autocorrelation = trending = correlated regime
    # Near 0 = random walk
    # Negative = mean-reverting
    score = 0.5 + autocorr * 0.5

    return max(0.0, min(1.0, score))
