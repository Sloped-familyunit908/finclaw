"""
Test: dynamic fallback regime — after 3+ consecutive fails in bull, 
temporarily downgrade to RANGING mode for entry logic.
This could help scenarios where bull regime is detected but price is still falling.
"""
import asyncio, random, math
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.backtester_v7 import BacktesterV7

def sim(start, days, ret, vol, seed=42, jp=0.02, js=0.04):
    rng = random.Random(seed); dt = 1/252; prices = [start]
    for _ in range(days-1):
        dW = rng.gauss(0, math.sqrt(dt))
        j = rng.gauss(0, js) if rng.random() < jp else 0
        prices.append(max(prices[-1]*math.exp((ret-0.5*vol**2)*dt+vol*dW+j), 0.01))
    base = datetime(2025,3,1)
    return [{'date':base+timedelta(days=i),'price':p,
             'volume':abs(random.Random(seed+i).gauss(p*1e6,p*5e5))} for i,p in enumerate(prices)]

async def quick_bench():
    """Quick benchmark - just sim scenarios, no crypto."""
    scenarios = [
        ("NVDA",    sim(500, 252, 0.80, 0.50, 1395)),
        ("AAPL",    sim(180, 252, 0.15, 0.25, 1002)),
        ("TSLA",    sim(250, 252, 0.40, 0.65, 1525)),
        ("META",    sim(550, 252,-0.20, 0.35, 1004)),
        ("AMZN",    sim(180, 252, 0.30, 0.35, 1628)),
        ("INTC",    sim(40,  252,-0.50, 0.40, 1006)),
        ("Moutai",  sim(1650,252, 0.05, 0.30, 2001, 0.03, 0.06)),
        ("CATL",    sim(220, 252, 0.55, 0.45, 1323, 0.03, 0.06)),
        ("CSI300",  sim(3800,252,-0.15, 0.25, 2003, 0.03, 0.06)),
    ]
    
    results = {}
    for name, h in scenarios:
        bh = h[-1]["price"]/h[0]["price"]-1
        bt = BacktesterV7(initial_capital=10000)
        r = await bt.run(name, "v7", h)
        results[name] = {"alpha": r.total_return - bh, "ret": r.total_return, "bh": bh}
    
    avg = sum(v["alpha"] for v in results.values()) / len(results)
    return results, avg

async def main():
    print("Quick benchmark (sim only)...")
    results, avg = await quick_bench()
    for name, v in results.items():
        print(f"  {name:<10} B&H={v['bh']:>+6.1%}  v7={v['ret']:>+6.1%}  alpha={v['alpha']:>+6.1%}")
    print(f"\nAvg alpha (9 scenarios): {avg:+.2%}")

asyncio.run(main())
