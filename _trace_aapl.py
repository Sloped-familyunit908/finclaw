"""Trace AAPL regime detection bar by bar"""
import asyncio, random, math
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.signal_engine_v7 import SignalEngineV7, MarketRegime

def sim(start, days, ret, vol, seed=42, jp=0.02, js=0.04):
    rng = random.Random(seed); dt = 1/252; prices = [start]
    for _ in range(days-1):
        dW = rng.gauss(0, math.sqrt(dt))
        j = rng.gauss(0, js) if rng.random() < jp else 0
        prices.append(max(prices[-1]*math.exp((ret-0.5*vol**2)*dt+vol*dW+j), 0.01))
    base = datetime(2025,3,1)
    return [{'date':base+timedelta(days=i),'price':p,
             'volume':abs(random.Random(seed+i).gauss(p*1e6,p*5e5))} for i,p in enumerate(prices)]

async def main():
    h = sim(180, 252, 0.15, 0.25, 1002)
    prices = [x["price"] for x in h]
    vols = [x.get("volume", 0) for x in h]
    
    engine = SignalEngineV7()
    print(f"{'bar':<5} {'price':>8} {'regime':<14} {'signal':<12} {'conf':>6} | entry logic")
    print("-"*75)
    
    entry_bars = [23, 28, 33, 65, 86, 110, 128, 160, 163]  # approximate trade entry bars
    
    for i in range(20, len(prices), 5):
        sig = engine.generate_signal(prices[:i+1], vols[:i+1])
        marker = "<< ENTRY?" if i in [x for x in range(20,252) if abs(i - x) < 3 and x in range(len(entry_bars))] else ""
        
        # Mark actual entry bars roughly
        p = prices[i]
        print(f"{i:<5} {p:>8.2f} {sig.regime.value:<14} {sig.signal:<12} {sig.confidence:>5.2f} {marker}")

asyncio.run(main())
