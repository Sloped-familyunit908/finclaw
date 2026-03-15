"""Quick diagnostic: compare v6 vs v7 per-scenario with trade details"""
import asyncio, random, math
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.backtester_v5 import BacktesterV5
from agents.backtester_v7 import BacktesterV7

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

async def main():
    test_cases = [
        ("NVDA (Bull)", sim(500, 252, 0.80, 0.50, 1395)),
        ("TSLA (Volatile)", sim(250, 252, 0.40, 0.65, 1525)),
        ("AMZN (Bull 2)", sim(180, 252, 0.30, 0.35, 1628)),
        ("META (Correction)", sim(550, 252, -0.20, 0.35, 1004)),
        ("Moutai (Sideways)", sim(1650, 252, 0.05, 0.30, 2001, 0.03, 0.06)),
        ("CATL (Growth)", sim(220, 252, 0.55, 0.45, 1323, 0.03, 0.06)),
    ]

    for name, h in test_cases:
        bh = h[-1]["price"] / h[0]["price"] - 1
        print(f"\n{'='*70}")
        print(f"  {name}  B&H: {bh:+.1%}")
        print(f"{'='*70}")

        for label, BT in [("v6", BacktesterV5), ("v7", BacktesterV7)]:
            bt = BT(initial_capital=10000)
            r = await bt.run("TEST", label, h)
            alpha = r.total_return - bh
            print(f"\n  {label}: ret={r.total_return:+.1%} alpha={alpha:+.1%} "
                  f"MaxDD={r.max_drawdown:.1%} trades={r.total_trades} WR={r.win_rate:.0%}")
            for t in r.trades:
                dur = (t.exit_time - t.entry_time).days
                print(f"    {t.signal_source:<12} entry={t.entry_price:.2f} exit={t.exit_price:.2f} "
                      f"pnl={t.pnl_pct:+.1%} dur={dur}d")

asyncio.run(main())
