import asyncio, random, math
from datetime import datetime, timedelta
import sys; sys.path.insert(0,'.')
from agents.signal_engine_v5 import SignalEngineV5

def sim(start, days, ret, vol, seed):
    rng = random.Random(seed)
    dt = 1/252; prices = [start]
    for _ in range(days-1):
        dW = rng.gauss(0, math.sqrt(dt))
        j = rng.gauss(0,0.04) if rng.random() < 0.02 else 0
        prices.append(max(prices[-1]*math.exp((ret-0.5*vol**2)*dt+vol*dW+j), 0.01))
    return prices

prices = sim(180, 252, 0.30, 0.35, 1628)
engine = SignalEngineV5()

print("AMZN Signal Trace (warmup=10)")
print(f"{'Bar':>4} {'Price':>8} {'Regime':>14} {'Signal':>10} {'Conf':>6}")
for i in range(10, 25):
    sig = engine.generate_signal(prices[:i+1])
    print(f"{i:4d} {prices[i]:8.2f} {sig.regime.value:>14} {sig.signal:>10} {sig.confidence:.2f}")
