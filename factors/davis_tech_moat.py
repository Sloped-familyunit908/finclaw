"""
Davis Double Play factor: Technology Moat (R&D intensity proxy)
Description: Identifies stocks with high technology barriers via price behavior.
Category: davis_double_play

Logic:
  Companies with real tech moats behave differently in the market:
  1. They outperform their sector consistently (源杰科技 vs 世嘉科技)
  2. They have higher "floor support" — dips are shallower and shorter
  3. They recover from market-wide drops faster

  Why? Because institutional investors KNOW the tech moat. They buy dips
  aggressively because the company can't be easily replaced.

  老板's insight: "技术实力最好的涨10倍，没技术的涨2倍就完了"

  Pure price-based proxy (no fundamental data needed):
  - Relative strength vs sector (outperformance)
  - Drawdown resilience (shallow dips = strong hands holding)
  - Recovery speed from local lows

Generated: 2026-03-24
"""

FACTOR_NAME = "davis_tech_moat"
FACTOR_DESC = "Technology moat proxy — sector outperformance + drawdown resilience"
FACTOR_CATEGORY = "davis_double_play"


def compute(closes, highs, lows, volumes, idx):
    """Detect tech moat stocks via price behavior.

    Stocks with true tech barriers show:
    1. Consistent outperformance (they go up more than peers)
    2. Shallow drawdowns (institutions defend the stock)
    3. Quick recovery from dips

    Returns 0-1 where >0.7 = likely has a tech moat.
    """
    lookback = 60
    if idx < lookback:
        return 0.5

    score = 0.0

    # --- 1. Trend quality (outperformance proxy) ---
    # A tech moat stock has a CLEAN uptrend, not choppy
    # Measure: how linear is the price path?
    total_return = (closes[idx] - closes[idx - lookback]) / closes[idx - lookback] if closes[idx - lookback] > 0 else 0

    if total_return <= 0:
        return max(0.1, 0.5 + total_return)

    # Path linearity: compare actual return to sum of abs daily returns
    sum_abs_returns = 0.0
    for i in range(idx - lookback + 1, idx + 1):
        if closes[i - 1] > 0:
            sum_abs_returns += abs(closes[i] - closes[i - 1]) / closes[i - 1]

    path_efficiency = abs(total_return) / sum_abs_returns if sum_abs_returns > 0 else 0.0
    # path_efficiency close to 1.0 = very linear (strong moat)
    # path_efficiency close to 0.0 = very choppy (no moat, speculative)

    if path_efficiency > 0.25:
        score += 0.15  # Very clean trend
    elif path_efficiency > 0.15:
        score += 0.10
    elif path_efficiency > 0.10:
        score += 0.05

    # --- 2. Drawdown resilience ---
    # Max drawdown in the period — shallow = institutional support
    peak = closes[idx - lookback]
    max_dd = 0.0
    for i in range(idx - lookback, idx + 1):
        if closes[i] > peak:
            peak = closes[i]
        dd = (closes[i] - peak) / peak if peak > 0 else 0
        if dd < max_dd:
            max_dd = dd

    # max_dd is negative. Closer to 0 = more resilient
    if max_dd > -0.08:
        score += 0.15  # Very shallow drawdown — strong hands
    elif max_dd > -0.15:
        score += 0.10
    elif max_dd > -0.20:
        score += 0.05

    # --- 3. Recovery speed ---
    # How quickly does the stock recover from its low?
    # Find the lowest point in last 60 days and measure recovery
    min_price = closes[idx - lookback]
    min_idx = idx - lookback
    for i in range(idx - lookback, idx + 1):
        if closes[i] < min_price:
            min_price = closes[i]
            min_idx = i

    if min_price > 0 and min_idx < idx - 5:
        recovery = (closes[idx] - min_price) / min_price
        days_since_low = idx - min_idx
        recovery_speed = recovery / days_since_low if days_since_low > 0 else 0

        if recovery_speed > 0.015:  # >1.5% per day recovery
            score += 0.10
        elif recovery_speed > 0.005:
            score += 0.05

    # --- 4. Higher lows pattern (institutional accumulation) ---
    # Split into 3 segments of 20 days, check if lows are rising
    low1 = min(closes[idx - 60:idx - 40]) if idx >= 60 else closes[idx - lookback]
    low2 = min(closes[idx - 40:idx - 20])
    low3 = min(closes[idx - 20:idx + 1])

    if low3 > low2 > low1:
        score += 0.10  # Rising lows — textbook institutional accumulation

    return max(0.0, min(1.0, 0.5 + score))
