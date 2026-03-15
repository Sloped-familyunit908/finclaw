"""
Deep diagnostic: which AHF scenarios are closest to flip?
And what's the exact trading pattern difference?
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

# AHF returns from benchmark (actual observed values):
AHF = {
    "NVDA":   +0.926,
    "AAPL":   -0.170,
    "TSLA":   +0.021,
    "META":   -0.282,
    "AMZN":   +0.499,
    "INTC":   -0.415,
    "Moutai": +0.615,
    "CATL":   +1.504,
    "CSI300": -0.117,
    "BTC":    +0.156,
    "ETH":    +1.562,
    "SOL":    +1.139,
}

async def main():
    scenarios = [
        ("NVDA",   sim(500,252,0.80,0.50,1395)),
        ("AAPL",   sim(180,252,0.15,0.25,1002)),
        ("TSLA",   sim(250,252,0.40,0.65,1525)),
        ("META",   sim(550,252,-0.20,0.35,1004)),
        ("AMZN",   sim(180,252,0.30,0.35,1628)),
        ("INTC",   sim(40,252,-0.50,0.40,1006)),
        ("Moutai", sim(1650,252,0.05,0.30,2001,0.03,0.06)),
        ("CATL",   sim(220,252,0.55,0.45,1323,0.03,0.06)),
        ("CSI300", sim(3800,252,-0.15,0.25,2003,0.03,0.06)),
    ]
    
    print(f"{'Scenario':<12} {'v7':>7} {'AHF':>7} {'gap':>8} | closest to flip?")
    print("-"*65)
    gaps = []
    for name, h in scenarios:
        bt = BacktesterV7(initial_capital=10000)
        r = await bt.run(name, "v7", h)
        ahf = AHF[name]
        gap = r.total_return - ahf
        wins = gap > 0
        gaps.append((name, r.total_return, ahf, gap))
        flag = "WIN!" if wins else f"need {-gap:+.1%} more"
        print(f"{'[W]' if wins else '[L]'} {name:<10} {r.total_return:>+6.1%} {ahf:>+6.1%}  {gap:>+7.1%} | {flag}")
    
    # Sort by closest gap (losses only)
    losses = sorted([(n,v7,ahf,g) for n,v7,ahf,g in gaps if g < 0], key=lambda x: x[3], reverse=True)
    print(f"\nClosest to flip (losses, sorted by gap):")
    for n,v7,ahf,g in losses:
        print(f"  {n:<10} v7={v7:+.1%} AHF={ahf:+.1%} gap={g:+.1%}")

asyncio.run(main())
