"""
Davis Double Play factor: Margin Expansion
Description: Detects expanding profit margins — price rising faster than costs.
Category: davis_double_play

Logic:
  When margins expand, EPS grows faster than revenue → P/E re-rating upward.
  This is the "E" in the Double Play: Earnings acceleration.

  Using price-volume as proxy:
  - Price rising on DECREASING relative volatility = orderly, confident markup
  - This mirrors how margin expansion works: steady price increases without wild swings
    suggest the company has pricing power (= fat margins)
  - Contrast: price rising on HIGH volatility = speculative, no pricing power

  技术壁垒高的公司（如源杰科技）涨价很稳，波动小——因为客户没得选。
  技术壁垒低的公司（如世嘉科技）涨幅不稳，波动大——随时被替代。

Generated: 2026-03-24
"""

FACTOR_NAME = "davis_margin_expansion"
FACTOR_DESC = "Margin expansion proxy — orderly price rise with declining volatility"
FACTOR_CATEGORY = "davis_double_play"


def compute(closes, highs, lows, volumes, idx):
    """Detect margin expansion via orderly price appreciation.

    High score when:
      - Price is trending up (positive return)
      - Volatility is DECLINING (confident, orderly move)
      - Volume is steady or increasing (institutional buying, not manipulation)

    This combination suggests pricing power — the hallmark of margin expansion.
    """
    lookback = 40
    if idx < lookback:
        return 0.5

    # --- Price trend ---
    if closes[idx - lookback] <= 0:
        return 0.5
    total_return = (closes[idx] - closes[idx - lookback]) / closes[idx - lookback]

    if total_return <= 0:
        # No margin expansion if price isn't going up
        return max(0.0, 0.5 + total_return * 2.0)  # mild penalty

    # --- Volatility trend (key signal) ---
    # Compare recent 10d volatility to prior 10d volatility
    import math

    def _std(data):
        n = len(data)
        if n < 2:
            return 0.0
        mean = sum(data) / n
        var = sum((x - mean) ** 2 for x in data) / (n - 1)
        return math.sqrt(var)

    # Recent volatility (last 10 days)
    recent_returns = []
    for i in range(idx - 9, idx + 1):
        if closes[i - 1] > 0:
            recent_returns.append((closes[i] - closes[i - 1]) / closes[i - 1])
    recent_vol = _std(recent_returns) if len(recent_returns) > 1 else 0.0

    # Prior volatility (20-30 days ago)
    prior_returns = []
    for i in range(idx - 29, idx - 19):
        if closes[i - 1] > 0:
            prior_returns.append((closes[i] - closes[i - 1]) / closes[i - 1])
    prior_vol = _std(prior_returns) if len(prior_returns) > 1 else 0.0

    score = 0.0

    # Price going up
    if total_return > 0.05:
        score += 0.15
    elif total_return > 0.02:
        score += 0.08

    # Volatility declining while price rises = STRONG margin expansion signal
    if prior_vol > 0:
        vol_ratio = recent_vol / prior_vol
        if vol_ratio < 0.6:
            score += 0.20  # Vol dropping sharply — very orderly, institutional
        elif vol_ratio < 0.8:
            score += 0.12  # Vol declining moderately
        elif vol_ratio < 1.0:
            score += 0.05  # Slightly lower vol

    # --- Consistency check ---
    # Count how many of the last 20 days were positive
    up_days = 0
    for i in range(idx - 19, idx + 1):
        if closes[i] > closes[i - 1]:
            up_days += 1
    win_rate = up_days / 20.0

    if win_rate > 0.65:
        score += 0.10  # Very consistent uptrend
    elif win_rate > 0.55:
        score += 0.05

    # --- Large-range days penalty ---
    # Margin expansion stocks don't have wild swings
    large_range_count = 0
    for i in range(idx - 19, idx + 1):
        if closes[i - 1] > 0:
            daily_range = abs(closes[i] - closes[i - 1]) / closes[i - 1]
            if daily_range > 0.05:  # >5% move
                large_range_count += 1
    if large_range_count >= 3:
        score -= 0.10  # Too many wild swings — not pricing power

    return max(0.0, min(1.0, 0.5 + score))
