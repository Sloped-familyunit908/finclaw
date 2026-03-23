"""
Factor: crypto_entropy_returns
Description: Entropy of return distribution (unpredictability)
Category: crypto
"""

FACTOR_NAME = "crypto_entropy_returns"
FACTOR_DESC = "Shannon entropy of return distribution"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Higher = more unpredictable returns."""
    lookback = 24
    if idx < lookback + 1:
        return 0.5

    returns = []
    for i in range(idx - lookback + 1, idx + 1):
        if closes[i - 1] > 0:
            returns.append((closes[i] - closes[i - 1]) / closes[i - 1])

    if len(returns) < 4:
        return 0.5

    # Bin returns into buckets for discrete entropy
    n_bins = 8
    min_r = min(returns)
    max_r = max(returns)

    if max_r == min_r:
        return 0.0  # No variability

    bin_width = (max_r - min_r) / n_bins
    counts = [0] * n_bins
    for r in returns:
        b = int((r - min_r) / bin_width)
        if b >= n_bins:
            b = n_bins - 1
        counts[b] += 1

    n = len(returns)
    entropy = 0.0
    import math
    for c in counts:
        if c > 0:
            p = c / n
            entropy -= p * math.log(p)

    # Max entropy for n_bins = log(n_bins)
    max_entropy = math.log(n_bins)
    if max_entropy <= 0:
        return 0.5

    score = entropy / max_entropy
    return max(0.0, min(1.0, score))
