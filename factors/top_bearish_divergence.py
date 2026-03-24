"""
Factor: top_bearish_divergence
Description: Price making new highs but RSI declining — bearish divergence
Category: top_escape
"""

FACTOR_NAME = "top_bearish_divergence"
FACTOR_DESC = "Price new highs but RSI declining — classic bearish divergence top signal"
FACTOR_CATEGORY = "top_escape"


def _calc_rsi(closes, end_idx, period=14):
    """Calculate RSI at a given index."""
    if end_idx < period:
        return 50.0

    gains = 0.0
    losses = 0.0
    for i in range(end_idx - period + 1, end_idx + 1):
        change = closes[i] - closes[i - 1]
        if change > 0:
            gains += change
        else:
            losses -= change

    avg_gain = gains / period
    avg_loss = losses / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _find_peaks(data, start, end, min_distance=3):
    """Find local peaks (indices) in data[start:end+1]."""
    peaks = []
    for i in range(start + 1, end):
        if data[i] > data[i - 1] and data[i] > data[i + 1]:
            if not peaks or (i - peaks[-1]) >= min_distance:
                peaks.append(i)
    return peaks


def compute(closes, highs, lows, volumes, idx):
    """Compare last 2 price peaks: if price[peak2] > price[peak1]
    but RSI[peak2] < RSI[peak1], that's bearish divergence.
    """
    lookback = 30
    if idx < lookback:
        return 0.5

    # Find peaks in highs over last 30 bars
    start = idx - lookback + 1
    peaks = _find_peaks(highs, start, idx)

    if len(peaks) < 2:
        return 0.5

    # Take last two peaks
    peak1 = peaks[-2]
    peak2 = peaks[-1]

    # Check if price made a higher high
    if highs[peak2] <= highs[peak1]:
        return 0.5  # No higher high, no divergence

    # Calculate RSI at both peaks
    rsi1 = _calc_rsi(closes, peak1)
    rsi2 = _calc_rsi(closes, peak2)

    # Bearish divergence: higher price but lower RSI
    if rsi2 >= rsi1:
        return 0.5  # RSI also rising, no divergence

    # Score based on strength of divergence
    price_diff_pct = (highs[peak2] - highs[peak1]) / highs[peak1] if highs[peak1] > 0 else 0
    rsi_diff = rsi1 - rsi2  # positive = RSI declining

    # Stronger divergence = higher score
    # RSI drop of 5+ points with price higher = strong signal
    divergence_strength = min(1.0, rsi_diff / 15.0)
    recency = 1.0 - ((idx - peak2) / lookback)  # more recent = stronger

    score = 0.6 + 0.4 * divergence_strength * recency

    return max(0.0, min(1.0, score))
