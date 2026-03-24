"""
Quality Factor: Resilience Score
==================================
How well did this stock hold up on the market's worst 5 days in the last 60?
If it dropped less than average on bad days = resilient/quality.
If it dropped more = weak/fragile.

Category: quality_filter
"""

FACTOR_NAME = "quality_resilience_score"
FACTOR_DESC = "Performance on worst days — resilient stocks drop less on bad days"
FACTOR_CATEGORY = "quality_filter"


def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0]."""
    lookback = 60
    if idx < lookback:
        lookback = idx + 1
    if lookback < 20:
        return 0.5

    # Compute daily returns over the lookback period
    daily_returns = []
    for i in range(idx - lookback + 2, idx + 1):
        if closes[i - 1] > 0:
            ret = (closes[i] - closes[i - 1]) / closes[i - 1]
            daily_returns.append((i, ret))

    if len(daily_returns) < 10:
        return 0.5

    # Find the worst 5 days (by return)
    sorted_days = sorted(daily_returns, key=lambda x: x[1])
    worst_n = min(5, len(sorted_days) // 4)  # at least bottom 25%
    if worst_n < 2:
        worst_n = 2

    worst_days = sorted_days[:worst_n]

    # Average return on worst days
    avg_worst_return = sum(r for _, r in worst_days) / len(worst_days)

    # Average return across ALL days (as baseline)
    avg_all_return = sum(r for _, r in daily_returns) / len(daily_returns)

    # If stock drops LESS than average on bad days, it's resilient
    # Resilience = how much better than average on the worst days
    # avg_worst_return is negative; less negative = more resilient
    if avg_all_return <= avg_worst_return:
        # Stock performs at least average on worst days — very resilient
        return 1.0

    # Ratio: how bad were worst days relative to average?
    # If worst days are much worse than average, stock is fragile
    diff = avg_worst_return - avg_all_return  # negative number
    # Map: diff of 0 -> 1.0 (resilient), diff of -0.05 -> 0.0 (fragile)
    score = 1.0 + diff / 0.05
    return max(0.0, min(1.0, score))
