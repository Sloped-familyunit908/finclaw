"""Debug Moutai entry timing"""
import asyncio, random, math
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.signal_engine_v6 import SignalEngineV6, MarketRegime as R6
from agents.signal_engine_v7 import SignalEngineV7, MarketRegime as R7

def sim(start, days, ret, vol, seed=42, jp=0.02, js=0.04):
    rng = random.Random(seed)
    dt = 1/252; prices = [start]
    for _ in range(days-1):
        dW = rng.gauss(0, math.sqrt(dt))
        j = rng.gauss(0,js) if rng.random() < jp else 0
        prices.append(max(prices[-1] * math.exp((ret-0.5*vol**2)*dt + vol*dW + j), 0.01))
    base = datetime(2025,3,1)
    return [{'date': base+timedelta(days=i), 'price': p,
             'volume': abs(rng.gauss(p*1e6, p*5e5))} for i,p in enumerate(prices)]

h = sim(1650, 252, 0.05, 0.30, 2001, 0.03, 0.06)
prices = [b["price"] for b in h]
volumes = [b.get("volume", 0) for b in h]

e6 = SignalEngineV6()
e7 = SignalEngineV7()

print(f"Moutai first 50 bars (signals when not in position):")
print(f"  {'Bar':>4} {'Price':>8} {'Regime6':>12} {'Sig6':>8} | {'Regime7':>12} {'Sig7':>8}")
print("  " + "-"*65)
for i in range(20, 55):
    s6 = e6.generate_signal(prices[:i+1], volumes[:i+1], 0)
    s7 = e7.generate_signal(prices[:i+1], volumes[:i+1], 0)
    mark = "<<" if s6.signal in ("buy","strong_buy") or s7.signal in ("buy","strong_buy") else ""
    print(f"  {i:>4} ${prices[i]:>7.1f} {s6.regime.value:>12} {s6.signal:>8} | "
          f"{s7.regime.value:>12} {s7.signal:>8} {mark}")
