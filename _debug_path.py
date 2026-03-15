import random, math
from datetime import datetime, timedelta

def sim(start, days, ret, vol, seed=42):
    rng = random.Random(seed)
    dt = 1/252; prices = [start]
    for _ in range(days-1):
        dW = rng.gauss(0, math.sqrt(dt))
        prices.append(max(prices[-1] * math.exp((ret-0.5*vol**2)*dt + vol*dW), 0.01))
    return prices

# NVDA: seed 1001
p = sim(500, 252, 0.80, 0.55, 1001)
print(f"NVDA (seed 1001): start=${p[0]:.0f} end=${p[-1]:.0f} ret={p[-1]/p[0]-1:+.1%}")
print(f"  Max=${max(p):.0f} at bar {p.index(max(p))}")
print(f"  Min after max=${min(p[p.index(max(p)):]):.0f}")
# Print path milestones
for i in [0, 50, 100, 150, 200, 251]:
    print(f"  Bar {i:3d}: ${p[i]:.0f} ({p[i]/p[0]-1:+.1%})")

print()

# TSLA: seed 1003
p2 = sim(250, 252, 0.30, 0.65, 1003)
print(f"TSLA (seed 1003): start=${p2[0]:.0f} end=${p2[-1]:.0f} ret={p2[-1]/p2[0]-1:+.1%}")
for i in [0, 50, 100, 150, 200, 251]:
    print(f"  Bar {i:3d}: ${p2[i]:.0f} ({p2[i]/p2[0]-1:+.1%})")

print()
# Show max drawdown in the path
def max_dd(prices):
    peak = prices[0]; mdd = 0
    for p in prices:
        peak = max(peak, p)
        dd = (p - peak)/peak
        mdd = min(mdd, dd)
    return mdd

print(f"NVDA path MaxDD: {max_dd(p):.1%}")
print(f"TSLA path MaxDD: {max_dd(p2):.1%}")
