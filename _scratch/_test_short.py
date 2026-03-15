"""
Quick test: v7+ Long/Short vs v7 Long-only
"""
import asyncio, random, math
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.backtester_v7 import BacktesterV7
from agents.backtester_v7plus import BacktesterV7Plus

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

    print(f"{'Scenario':<12} {'B&H':>7} | {'v7':>7} {'a_v7':>7} | {'v7+':>7} {'a_v7+':>7} | {'delta':>7}")
    print("-"*72)

    v7_alphas = []; v7p_alphas = []

    for name, h in scenarios:
        bh = h[-1]["price"]/h[0]["price"]-1

        bt7 = BacktesterV7(initial_capital=10000)
        r7 = await bt7.run(name, "v7", h)
        a7 = r7.total_return - bh

        bt7p = BacktesterV7Plus(initial_capital=10000, enable_short=True)
        r7p = await bt7p.run(name, "v7+", h)
        a7p = r7p.total_return - bh

        delta = a7p - a7
        v7_alphas.append(a7); v7p_alphas.append(a7p)

        tag = "+" if delta > 0.005 else ("-" if delta < -0.005 else "=")
        print(f"[{tag}] {name:<10} {bh:>+6.1%} | {r7.total_return:>+6.1%} {a7:>+6.1%} | "
              f"{r7p.total_return:>+6.1%} {a7p:>+6.1%} | {delta:>+6.2%}")

    avg_v7 = sum(v7_alphas)/len(v7_alphas)
    avg_v7p = sum(v7p_alphas)/len(v7p_alphas)
    print(f"\nAvg alpha: v7={avg_v7:+.2%}  v7+={avg_v7p:+.2%}  delta={avg_v7p-avg_v7:+.2%}")

asyncio.run(main())
