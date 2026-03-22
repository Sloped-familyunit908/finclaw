FACTOR_NAME = "entropy_volume"
FACTOR_DESC = "Shannon entropy of volume distribution over 20 days — high = unpredictable"
FACTOR_CATEGORY = "statistical"
LOOKBACK = 20

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    # Discretize volume into bins relative to average
    vols = []
    for i in range(idx - LOOKBACK + 1, idx + 1):
        vols.append(float(volumes[i]))
    total_vol = sum(vols)
    if total_vol == 0:
        return 0.5
    # Compute probabilities
    probs = [v / total_vol for v in vols]
    # Shannon entropy: -sum(p * log(p))
    # Use log approximation: ln(x) ≈ (x-1) - (x-1)²/2 + ... for x near 1
    # Better: use repeated squaring or natural log identity
    entropy = 0.0
    for p in probs:
        if p > 0:
            # ln(p) approximation using ln(p) = ln(p/ref) + ln(ref)
            # Simple iterative: ln(x) for x in (0,1]
            # ln(1/n) = -ln(n), max entropy = ln(n)
            # Use: ln(x) ≈ 2 * sum of ((x-1)/(x+1))^(2k+1) / (2k+1))
            x = p
            if x <= 0:
                continue
            # Compute ln(x) via series
            ratio = (x - 1.0) / (x + 1.0)
            ratio2 = ratio * ratio
            ln_x = 0.0
            term = ratio
            for k in range(15):
                ln_x += term / (2 * k + 1)
                term *= ratio2
            ln_x *= 2.0
            entropy -= p * ln_x
    # Max entropy = ln(20) ≈ 3.0
    # Normalize to [0, 1]
    # Lower entropy = more predictable volume pattern
    # Higher entropy = random = neutral
    score = 0.5 + (entropy - 2.5) * 0.2
    return max(0.0, min(1.0, score))
