import random, math
from datetime import datetime, timedelta

def sim(start, days, ret, vol, seed=42):
    rng = random.Random(seed)
    dt = 1/252; prices = [start]
    for _ in range(days-1):
        dW = rng.gauss(0, math.sqrt(dt))
        prices.append(max(prices[-1] * math.exp((ret-0.5*vol**2)*dt + vol*dW), 0.01))
    return prices

def max_dd(prices):
    peak = prices[0]; mdd = 0
    for p in prices:
        peak = max(peak, p)
        dd = (p-peak)/peak
        mdd = min(mdd, dd)
    return mdd

# Find good seeds where final return is close to expected
print("Finding good seeds for each stock...")
print()

# NVDA: expect +60-100% annual return, low MaxDD
for stock, start, target_ret, vol, target_mdd in [
    ("NVDA Bull",  500, (0.60, 1.20), 0.50, -0.50),
    ("TSLA Vol",   250, (0.20, 0.60), 0.65, -0.45),
    ("CATL Growth",220, (0.30, 0.80), 0.45, -0.45),
    ("AMZN Bull2", 180, (0.15, 0.50), 0.35, -0.40),
]:
    lo_ret, hi_ret = target_ret
    good_seeds = []
    for s in range(1000, 2000):
        p = sim(start, 252, (lo_ret+hi_ret)/2, vol, s)
        r = p[-1]/p[0]-1
        mdd = max_dd(p)
        if lo_ret <= r <= hi_ret and mdd > target_mdd:
            good_seeds.append((s, r, mdd))
    if good_seeds:
        best = sorted(good_seeds, key=lambda x: x[1])[-1]
        print(f"{stock}: best seed={best[0]} ret={best[1]:+.1%} maxdd={best[2]:.1%}")
    else:
        print(f"{stock}: no good seeds in range {lo_ret:.0%}-{hi_ret:.0%}")
