"""
Davis Double Play factor: New Demand Catalyst
Description: Detects sudden regime change in price behavior — new demand entering.
Category: davis_double_play

Logic:
  The MOST IMPORTANT factor per 老板: new demand > everything else.

  When genuinely new demand enters a stock/sector, the price behavior CHANGES:
  - Overnight gaps start appearing (institutions buying at open)
  - Price gaps up and HOLDS (doesn't fill — real buying vs speculation)
  - Correlation with sector breaks (stock decouples from dying sector)
  - Weekend gaps appear (news-driven buyers entering)

  This captures the MOMENT the market realizes "wait, there's new demand here."
  Long飞光纤's inflection: it started gapping up on AI datacenter news while
  other telecom stocks did nothing.

  This factor focuses on BEHAVIORAL CHANGE — the stock doing something
  it hasn't done before — which is the earliest signal of new demand.

Generated: 2026-03-24
"""

FACTOR_NAME = "davis_new_demand_catalyst"
FACTOR_DESC = "Behavioral regime change — sudden new demand entering (最重要因子)"
FACTOR_CATEGORY = "davis_double_play"


def compute(closes, highs, lows, volumes, idx):
    """Detect new demand catalyst via behavioral regime change.

    Core signals:
    1. Gap-up frequency increasing (institutions buying at open)
    2. Gaps NOT filling (real demand, not speculation)
    3. Volume regime shift (from low-vol to high-vol)
    4. Price action quality change (from choppy to trending)

    This is designed to be the highest-weighted Davis factor.
    Returns 0-1 where >0.7 = strong new demand signal.
    """
    lookback = 40
    if idx < lookback:
        return 0.5

    score = 0.0

    # --- 1. Gap-up frequency (recent vs prior) ---
    # A gap-up = today's low > yesterday's close (gap hasn't been filled)
    recent_gaps = 0
    prior_gaps = 0

    # Recent 10 days
    for i in range(idx - 9, idx + 1):
        if lows[i] > closes[i - 1] * 1.005:  # 0.5%+ gap up
            recent_gaps += 1

    # Prior 10 days
    for i in range(idx - 19, idx - 9):
        if lows[i] > closes[i - 1] * 1.005:
            prior_gaps += 1

    if recent_gaps > prior_gaps and recent_gaps >= 2:
        score += 0.12  # More gaps recently — new buyers arriving

    # --- 2. Unfilled gap-ups (true demand) ---
    unfilled_gaps = 0
    for i in range(idx - 14, idx + 1):
        if lows[i] > closes[i - 1] * 1.005:
            # Check if gap held: subsequent days stayed above gap level
            gap_level = closes[i - 1]
            gap_held = True
            for j in range(i + 1, min(i + 4, idx + 1)):
                if lows[j] < gap_level:
                    gap_held = False
                    break
            if gap_held:
                unfilled_gaps += 1

    if unfilled_gaps >= 2:
        score += 0.15  # Multiple unfilled gaps — very strong demand
    elif unfilled_gaps >= 1:
        score += 0.08

    # --- 3. Volume regime shift ---
    # Compare volume coefficient of variation (stability)
    import math

    def _cv(data):
        n = len(data)
        if n < 2:
            return 0.0
        mean = sum(data) / n
        if mean <= 0:
            return 0.0
        var = sum((x - mean) ** 2 for x in data) / (n - 1)
        return math.sqrt(var) / mean

    recent_vols = [volumes[i] for i in range(idx - 9, idx + 1)]
    prior_vols = [volumes[i] for i in range(idx - 39, idx - 9)]

    recent_mean_vol = sum(recent_vols) / len(recent_vols)
    prior_mean_vol = sum(prior_vols) / len(prior_vols)

    # Volume level jump
    if prior_mean_vol > 0:
        vol_ratio = recent_mean_vol / prior_mean_vol
        if vol_ratio > 2.5:
            score += 0.12  # Volume regime SHIFT (not just a spike)
        elif vol_ratio > 1.8:
            score += 0.08
        elif vol_ratio > 1.3:
            score += 0.04

    # --- 4. Trend quality change ---
    # Prior period: choppy (low autocorrelation)
    # Recent period: trending (high autocorrelation)
    def _autocorr(data):
        n = len(data)
        if n < 4:
            return 0.0
        mean = sum(data) / n
        var = sum((x - mean) ** 2 for x in data)
        if var == 0:
            return 0.0
        cov = sum((data[i] - mean) * (data[i - 1] - mean) for i in range(1, n))
        return cov / var

    recent_returns = []
    for i in range(idx - 14, idx + 1):
        if closes[i - 1] > 0:
            recent_returns.append((closes[i] - closes[i - 1]) / closes[i - 1])

    prior_returns = []
    for i in range(idx - 34, idx - 14):
        if closes[i - 1] > 0:
            prior_returns.append((closes[i] - closes[i - 1]) / closes[i - 1])

    recent_autocorr = _autocorr(recent_returns)
    prior_autocorr = _autocorr(prior_returns)

    # Transition from mean-reverting (negative autocorr) to trending (positive autocorr)
    if recent_autocorr > 0.1 and prior_autocorr < 0.05:
        score += 0.10  # Regime changed from choppy to trending

    # --- 5. Opening strength ---
    # New demand often shows as strong opens (gap & go)
    strong_opens = 0
    for i in range(idx - 9, idx + 1):
        # Proxy: if low > yesterday close AND close > open proxy (close near high)
        if lows[i] > closes[i - 1] and closes[i] > (highs[i] + lows[i]) / 2:
            strong_opens += 1

    if strong_opens >= 3:
        score += 0.06  # Consistent strong opens — demand at open

    return max(0.0, min(1.0, 0.5 + score))
