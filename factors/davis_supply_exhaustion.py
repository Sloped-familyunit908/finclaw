"""
Davis Double Play factor: Supply Exhaustion
Description: Detects late-stage supply cleanup — the industry is done bleeding.
Category: davis_double_play

Logic:
  After an industry bleeds for 2+ years, supply is exhausted when:
  1. The stock stops making new lows (sellers exhausted)
  2. Volume dries up at the bottom (no one left to sell)
  3. Price starts forming a base (flat, not falling)

  This is the FLOOR. The price can't go lower because everyone who wanted
  to sell has already sold.

  老板's caveat: "没有需求，你再出清也没有用" — this factor alone means
  nothing. It must combine with demand factors. That's why the evolution engine
  will assign it lower weight if demand factors are more predictive.

  Pure price-based (works for any market):
  - No new lows in 20 days (selling exhaustion)
  - Volume at lowest levels in 60 days (capitulation complete)
  - Price range contracting (base forming)
  - Then a first sign of life: price ticking up from base

Generated: 2026-03-24
"""

FACTOR_NAME = "davis_supply_exhaustion"
FACTOR_DESC = "Supply cleanup exhaustion — bottom formation after prolonged decline"
FACTOR_CATEGORY = "davis_double_play"


def compute(closes, highs, lows, volumes, idx):
    """Detect supply exhaustion bottom.

    This is the setup BEFORE the double play starts.
    High score = industry may have finished bleeding.

    Returns 0-1 where >0.7 = strong exhaustion signal.
    """
    long_lookback = 60
    if idx < long_lookback:
        return 0.5

    score = 0.0

    # --- 1. Prior decline required ---
    # Must have fallen significantly in the past (otherwise it's not a recovery)
    if closes[idx - 60] <= 0:
        return 0.5
    long_return = (closes[idx] - closes[idx - 60]) / closes[idx - 60]

    # We want stocks that HAVE declined but are NOW stabilizing
    # Not stocks that are still falling hard
    recent_return = (closes[idx] - closes[idx - 20]) / closes[idx - 20] if closes[idx - 20] > 0 else 0

    # Ideal: long-term down but recent flat or slightly up
    prior_drop = (closes[idx - 20] - closes[idx - 60]) / closes[idx - 60] if closes[idx - 60] > 0 else 0

    if prior_drop < -0.15:
        # Good — there was a significant prior decline
        score += 0.10
        if prior_drop < -0.30:
            score += 0.05  # Deep decline = more exhaustion potential

    if recent_return > -0.02 and recent_return < 0.10:
        # Recent period is flat — base forming
        score += 0.10

    # --- 2. No new lows ---
    low_20d = min(closes[idx - 19:idx + 1])
    low_60d = min(closes[idx - 59:idx + 1])

    if low_20d >= low_60d * 0.98:
        # 20d low is near or above 60d low — stopped making new lows
        score += 0.10

    # --- 3. Volume exhaustion ---
    # Average volume in last 10 days vs prior 50 days
    recent_vol = sum(volumes[idx - 9:idx + 1]) / 10.0
    prior_vol = sum(volumes[idx - 59:idx - 9]) / 50.0

    if prior_vol > 0:
        vol_ratio = recent_vol / prior_vol
        if vol_ratio < 0.5:
            score += 0.10  # Volume dried up — nobody selling anymore
        elif vol_ratio < 0.7:
            score += 0.05

    # --- 4. Range contraction (base forming) ---
    recent_range_total = 0.0
    prior_range_total = 0.0

    for i in range(idx - 9, idx + 1):
        if closes[i - 1] > 0:
            recent_range_total += abs(highs[i] - lows[i]) / closes[i - 1]
    for i in range(idx - 29, idx - 19):
        if closes[i - 1] > 0:
            prior_range_total += abs(highs[i] - lows[i]) / closes[i - 1]

    recent_avg_range = recent_range_total / 10.0
    prior_avg_range = prior_range_total / 10.0

    if prior_avg_range > 0 and recent_avg_range < prior_avg_range * 0.7:
        score += 0.08  # Ranges tightening — base

    # --- 5. First sign of life ---
    # Price just turned up from the base
    if recent_return > 0.02 and recent_return < 0.15:
        if closes[idx] > closes[idx - 5]:
            score += 0.08  # First uptick after flat base

    return max(0.0, min(1.0, 0.5 + score))
