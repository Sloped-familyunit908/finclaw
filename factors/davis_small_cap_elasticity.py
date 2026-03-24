"""
Davis Double Play factor: Small Cap Elasticity
Description: Detects small-cap stocks with outsized momentum — 5-10x candidates.
Category: davis_double_play

Logic:
  10x stocks almost always start as small/mid caps (<300亿).
  Large caps (>1000亿) can't 10x — they're too big.

  长飞光纤 from 100亿 → 1800亿 = 18x potential
  紫金矿业 from 5000亿 → hard to go even 2x

  Since we don't have direct market cap data in the standard factor interface,
  we use PRICE LEVEL as a proxy:
  - Very low-priced stocks (<15 yuan) with strong momentum = high elasticity
  - Mid-priced stocks (15-50 yuan) with strong momentum = medium elasticity
  - High-priced stocks (>100 yuan) already de-risked = lower remaining upside

  Combined with momentum quality to filter garbage small caps.

Generated: 2026-03-24
"""

FACTOR_NAME = "davis_small_cap_elasticity"
FACTOR_DESC = "Small cap with strong momentum — high elasticity for 5-10x returns"
FACTOR_CATEGORY = "davis_double_play"


def compute(closes, highs, lows, volumes, idx):
    """Detect high-elasticity small caps with strong momentum.

    Not all small caps are good — only those showing:
    1. Strong price momentum (already moving)
    2. Increasing volume (institutional attention)
    3. Breaking out of long-term range

    Returns 0-1 where >0.7 = high elasticity candidate.
    """
    lookback = 60
    if idx < lookback:
        return 0.5

    score = 0.0
    current_price = closes[idx]

    # --- 1. Price level (elasticity proxy) ---
    # This is imperfect but directionally correct
    # Small caps tend to have lower absolute prices in A-shares
    if current_price < 20:
        price_elasticity = 0.10  # High elasticity zone
    elif current_price < 50:
        price_elasticity = 0.05  # Medium
    else:
        price_elasticity = 0.0   # Large/expensive — less elastic

    score += price_elasticity

    # --- 2. Momentum quality ---
    if closes[idx - 60] <= 0:
        return 0.5
    return_60d = (closes[idx] - closes[idx - 60]) / closes[idx - 60]
    return_20d = (closes[idx] - closes[idx - 20]) / closes[idx - 20] if closes[idx - 20] > 0 else 0

    # Strong momentum
    if return_60d > 0.30:
        score += 0.15  # Up 30%+ in 60 days — serious move
    elif return_60d > 0.15:
        score += 0.08
    elif return_60d > 0.05:
        score += 0.03

    # Recent acceleration
    if return_20d > 0.10 and return_60d > 0.15:
        score += 0.05  # Recent period even stronger

    # --- 3. Volume surge (institutional discovery) ---
    recent_vol = sum(volumes[idx - 9:idx + 1]) / 10.0
    prior_vol = sum(volumes[idx - 59:idx - 9]) / 50.0

    if prior_vol > 0:
        vol_expansion = recent_vol / prior_vol
        if vol_expansion > 3.0:
            score += 0.10  # Volume exploding — being "discovered"
        elif vol_expansion > 2.0:
            score += 0.08
        elif vol_expansion > 1.5:
            score += 0.05

    # --- 4. Breaking out of range ---
    # Is current price near 60-day high? (breakout territory)
    high_60d = max(highs[idx - 59:idx + 1])
    if high_60d > 0:
        distance_from_high = (closes[idx] - high_60d) / high_60d
        if distance_from_high > -0.03:
            score += 0.08  # At or near 60d high — breakout
        elif distance_from_high > -0.10:
            score += 0.03

    # --- 5. Penalty: Too expensive or too low volume ---
    if current_price > 200:
        score -= 0.10  # Already very expensive — less upside
    
    # Min volume check — avoid illiquid garbage
    if recent_vol < 100000:
        return 0.3  # Too illiquid — can't be a real 10x candidate

    return max(0.0, min(1.0, 0.5 + score))
