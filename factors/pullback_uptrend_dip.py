"""
Factor: pullback_uptrend_dip
Description: THE KEY FACTOR — buy the dip in a bull stock. Score 1.0 when
  60-day MA slope positive (long-term uptrend), price above 60-day MA,
  BUT 5-day RSI < 40 (short-term dip). Score 0.0 in downtrends.
Category: pullback_strategy
"""

FACTOR_NAME = "pullback_uptrend_dip"
FACTOR_DESC = (
    "Uptrend dip: 60d MA rising + price above MA60 + RSI5 < 40 = buy the dip"
)
FACTOR_CATEGORY = "pullback_strategy"


def _calc_ma(closes, end_idx, period):
    """Simple moving average ending at end_idx (inclusive)."""
    if end_idx < period - 1:
        return None
    return sum(closes[end_idx - period + 1 : end_idx + 1]) / period


def _calc_rsi(closes, end_idx, period=5):
    """Wilder-style RSI over *period* bars ending at end_idx."""
    if end_idx < period:
        return None
    gains = 0.0
    losses = 0.0
    for i in range(end_idx - period + 1, end_idx + 1):
        delta = closes[i] - closes[i - 1]
        if delta > 0:
            gains += delta
        else:
            losses -= delta  # make positive
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def compute(closes, highs, lows, volumes, idx):
    """
    Core logic
    ----------
    1. MA60 slope positive  → long-term uptrend intact
    2. Price > MA60          → still in uptrend territory
    3. RSI(5) < 40           → short-term pullback / oversold dip

    All three met  → score ≈ 0.85–1.0  (ideal buy-the-dip)
    MA60 slope <= 0 → 0.0  (downtrend — avoid falling knives)
    """
    lookback = 65  # need at least 60 bars + a few for slope
    if idx < lookback:
        return 0.5

    ma60_now = _calc_ma(closes, idx, 60)
    ma60_prev = _calc_ma(closes, idx - 5, 60)

    if ma60_now is None or ma60_prev is None or ma60_prev <= 0:
        return 0.5

    # ── Condition 1: MA60 slope ──
    ma60_slope = (ma60_now - ma60_prev) / ma60_prev
    if ma60_slope <= 0:
        return 0.0  # downtrend — hard zero

    # ── Condition 2: price above MA60 ──
    if ma60_now <= 0:
        return 0.5
    price_vs_ma60 = (closes[idx] - ma60_now) / ma60_now
    if price_vs_ma60 < 0:
        # Below MA60 — might be breaking down; small credit if barely below
        if price_vs_ma60 < -0.03:
            return 0.15  # too far below, uptrend questionable
        # Within 3% below — give partial credit
        above_score = 0.3
    else:
        above_score = min(1.0, 0.6 + price_vs_ma60 * 5)  # closer = fine, very far above = OK too

    # ── Condition 3: RSI(5) < 40 ──
    rsi5 = _calc_rsi(closes, idx, 5)
    if rsi5 is None:
        return 0.5

    if rsi5 >= 50:
        return 0.5  # no dip happening
    if rsi5 >= 40:
        # Slight pullback — mild signal
        rsi_score = 0.3
    elif rsi5 >= 25:
        # Sweet spot: meaningful dip but not crash
        rsi_score = 0.8 + (40 - rsi5) / 75  # 0.8 – 1.0
    else:
        # RSI < 25: very oversold, could be crash even in uptrend
        rsi_score = 0.7

    # ── Slope strength bonus ──
    slope_strength = min(1.0, ma60_slope / 0.02)  # 2% over 5 days = max

    # ── Combine ──
    score = 0.5 + 0.5 * above_score * rsi_score * slope_strength

    return max(0.0, min(1.0, score))
