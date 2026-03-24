"""
Quality Factor: Momentum Rank
================================
Rank the stock's 20-day momentum within its "peer group"
(group by price range as proxy for sector).
Stocks in the bottom 30% of their peer group = weak relative to peers.

Category: quality_filter
"""

FACTOR_NAME = "quality_momentum_rank"
FACTOR_DESC = "20-day momentum rank within price-range peer group"
FACTOR_CATEGORY = "quality_filter"


def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0].

    Since individual factor compute only sees one stock's data, we use
    the stock's own historical momentum distribution as proxy for peer ranking.
    The stock's current 20d momentum is ranked against its historical
    20d momentum values over the last 120 days.
    """
    mom_period = 20
    hist_window = 120

    if idx < mom_period:
        return 0.5

    # Current 20-day momentum
    if closes[idx - mom_period] <= 0:
        return 0.5
    current_mom = (closes[idx] - closes[idx - mom_period]) / closes[idx - mom_period]

    # Collect historical 20-day momentum values
    hist_start = max(mom_period, idx - hist_window)
    historical_moms = []
    for i in range(hist_start, idx + 1):
        if closes[i - mom_period] > 0:
            m = (closes[i] - closes[i - mom_period]) / closes[i - mom_period]
            historical_moms.append(m)

    if len(historical_moms) < 10:
        return 0.5

    # Rank current momentum within historical distribution
    count_below = sum(1 for m in historical_moms if m < current_mom)
    rank_pct = count_below / len(historical_moms)

    return max(0.0, min(1.0, rank_pct))
