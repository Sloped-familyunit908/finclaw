"""
Factor: pullback_rsi_divergence_in_uptrend
Description: Price in uptrend (above MA60), RSI pulled back to 30-40 zone,
  MACD still positive. "Oversold within an uptrend" = best buy signal.
Category: pullback_strategy
"""

FACTOR_NAME = "pullback_rsi_divergence_in_uptrend"
FACTOR_DESC = (
    "Oversold RSI (30-40) in uptrend with positive MACD — prime dip buy"
)
FACTOR_CATEGORY = "pullback_strategy"


def _calc_ma(closes, end_idx, period):
    """Simple moving average ending at end_idx (inclusive)."""
    if end_idx < period - 1:
        return None
    return sum(closes[end_idx - period + 1 : end_idx + 1]) / period


def _calc_rsi(closes, end_idx, period=14):
    """Wilder-style RSI."""
    if end_idx < period:
        return None
    gains = 0.0
    losses = 0.0
    for i in range(end_idx - period + 1, end_idx + 1):
        delta = closes[i] - closes[i - 1]
        if delta > 0:
            gains += delta
        else:
            losses -= delta
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def _calc_ema(values, period):
    """Exponential moving average — returns list same length as values."""
    if not values:
        return []
    ema = [values[0]]
    k = 2.0 / (period + 1)
    for i in range(1, len(values)):
        ema.append(values[i] * k + ema[-1] * (1 - k))
    return ema


def _calc_macd_hist(closes, end_idx):
    """Return MACD histogram value at end_idx, or None."""
    if end_idx < 33:  # need 26 + 9 - 2
        return None
    subset = closes[: end_idx + 1]
    ema12 = _calc_ema(subset, 12)
    ema26 = _calc_ema(subset, 26)
    macd_line = [ema12[i] - ema26[i] for i in range(len(subset))]
    signal = _calc_ema(macd_line, 9)
    return macd_line[-1] - signal[-1]  # histogram


def compute(closes, highs, lows, volumes, idx):
    """
    Conditions
    ----------
    1. Price above MA60 → uptrend
    2. RSI(14) in 30-40  → oversold pullback
    3. MACD histogram > 0 or MACD line > 0 → momentum still bullish

    All three → high score.  Missing any → neutral/low.
    """
    if idx < 65:
        return 0.5

    # ── Condition 1: uptrend (price > MA60) ──
    ma60 = _calc_ma(closes, idx, 60)
    if ma60 is None or ma60 <= 0:
        return 0.5

    price_vs_ma60 = (closes[idx] - ma60) / ma60
    if price_vs_ma60 < -0.02:
        return 0.2  # below MA60 — not in uptrend

    if price_vs_ma60 < 0:
        uptrend_score = 0.5  # barely below, partial credit
    else:
        uptrend_score = min(1.0, 0.7 + price_vs_ma60 * 3)

    # ── Condition 2: RSI in 30-40 zone ──
    rsi = _calc_rsi(closes, idx, 14)
    if rsi is None:
        return 0.5

    if rsi < 20:
        rsi_score = 0.5  # too oversold — could be crash
    elif rsi < 30:
        rsi_score = 0.7  # very oversold, risky but potentially great
    elif rsi <= 40:
        rsi_score = 1.0  # sweet spot
    elif rsi <= 45:
        rsi_score = 0.4  # slightly below midpoint
    else:
        return 0.5  # not oversold at all

    # ── Condition 3: MACD still positive ──
    # Use MACD line (EMA12 - EMA26) > 0 as primary check
    subset = closes[: idx + 1]
    ema12 = _calc_ema(subset, 12)
    ema26 = _calc_ema(subset, 26)
    macd_line_val = ema12[-1] - ema26[-1]

    if macd_line_val <= 0:
        return 0.3  # MACD negative — momentum already turned bearish

    # Normalize MACD strength (relative to price)
    macd_strength = macd_line_val / closes[idx] if closes[idx] > 0 else 0
    macd_score = min(1.0, macd_strength / 0.02)  # 2% = max

    # ── Combine ──
    score = 0.5 + 0.5 * uptrend_score * rsi_score * macd_score

    return max(0.0, min(1.0, score))
