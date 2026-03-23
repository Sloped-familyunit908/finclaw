"""
Factor: crypto_gap_fill
Description: After >2% gap, probability of gap fill
Category: crypto
"""

FACTOR_NAME = "crypto_gap_fill"
FACTOR_DESC = "Gap fill probability — after >2% gap, measures likelihood of fill"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = gap up filling (bearish mean reversion), Low = gap down filling (bullish)."""
    if idx < 24:
        return 0.5

    if closes[idx - 1] <= 0:
        return 0.5

    # Check for gap (using close-to-close since crypto has no open)
    gap_pct = (closes[idx] - closes[idx - 1]) / closes[idx - 1]

    if abs(gap_pct) < 0.02:
        # No significant gap
        return 0.5

    # Check historical gap fill rate (how often gaps fill in lookback)
    lookback = 24
    gaps_up_filled = 0
    gaps_down_filled = 0
    gaps_up_total = 0
    gaps_down_total = 0

    for i in range(max(1, idx - lookback), idx):
        if closes[i - 1] <= 0:
            continue
        g = (closes[i] - closes[i - 1]) / closes[i - 1]
        if g > 0.02:
            gaps_up_total += 1
            # Check if gap filled (price came back to pre-gap level)
            for j in range(i + 1, min(i + 6, idx + 1)):
                if closes[j] <= closes[i - 1]:
                    gaps_up_filled += 1
                    break
        elif g < -0.02:
            gaps_down_total += 1
            for j in range(i + 1, min(i + 6, idx + 1)):
                if closes[j] >= closes[i - 1]:
                    gaps_down_filled += 1
                    break

    # Current gap signal
    if gap_pct > 0.02:
        # Gap up — mean reversion predicts fill (bearish)
        fill_rate = gaps_up_filled / gaps_up_total if gaps_up_total > 0 else 0.6
        gap_strength = min(gap_pct / 0.05, 1.0)
        score = 0.5 - fill_rate * gap_strength * 0.4
    elif gap_pct < -0.02:
        # Gap down — mean reversion predicts fill (bullish)
        fill_rate = gaps_down_filled / gaps_down_total if gaps_down_total > 0 else 0.6
        gap_strength = min(abs(gap_pct) / 0.05, 1.0)
        score = 0.5 + fill_rate * gap_strength * 0.4
    else:
        score = 0.5

    return max(0.0, min(1.0, score))
