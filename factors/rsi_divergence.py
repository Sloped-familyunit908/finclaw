"""
Auto-generated factor: rsi_divergence
Description: Price making new low but RSI isn't (bullish divergence)
Category: mean_reversion
Generated: seed
"""

FACTOR_NAME = "rsi_divergence"
FACTOR_DESC = "Price making new low but RSI isn't (bullish divergence)"
FACTOR_CATEGORY = "mean_reversion"


def compute(closes, highs, lows, volumes, idx):
    """Detect bullish RSI divergence: price new low, RSI higher low."""

    lookback = 30
    rsi_period = 14
    if idx < lookback + rsi_period:
        return 0.5

    # Compute RSI at a given index
    def _rsi_at(end_idx):
        gains = 0.0
        losses = 0.0
        for j in range(end_idx - rsi_period + 1, end_idx + 1):
            change = closes[j] - closes[j - 1]
            if change > 0:
                gains += change
            else:
                losses -= change
        avg_gain = gains / rsi_period
        avg_loss = losses / rsi_period
        if avg_loss < 1e-10:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    # Find price low in lookback window
    current_price = closes[idx]
    min_price = current_price
    min_price_idx = idx
    for i in range(idx - lookback, idx):
        if closes[i] < min_price:
            min_price = closes[i]
            min_price_idx = i

    # Check if current price is near/at new low
    price_at_new_low = current_price <= min_price * 1.02

    if not price_at_new_low:
        return 0.5

    # Compare RSI at current vs RSI at prior low
    rsi_now = _rsi_at(idx)
    rsi_at_low = _rsi_at(min_price_idx) if min_price_idx >= rsi_period else rsi_now

    # Bullish divergence: price at new low but RSI higher
    if rsi_now > rsi_at_low + 2:
        divergence = (rsi_now - rsi_at_low) / 50.0
        score = 0.5 + divergence
        return max(0.0, min(1.0, score))

    return 0.5
