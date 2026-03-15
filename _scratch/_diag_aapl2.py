"""Deep dive AAPL: need +0.9% more to beat AHF=-17.0%"""
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

async def main():
    h = sim(180, 252, 0.15, 0.25, 1002)
    bh = h[-1]["price"]/h[0]["price"]-1

    bt = BacktesterV7(initial_capital=10000)
    r = await bt.run("AAPL", "v7", h)
    print(f"AAPL: B&H={bh:+.1%}  v7={r.total_return:+.1%}  AHF=-17.0%")
    print(f"trades={r.total_trades}  WR={r.win_rate:.0%}  MaxDD={r.max_drawdown:+.1%}")
    print(f"\nTrade log:")
    total_pnl_pct = 0
    for t in r.trades:
        dur = max((t.exit_time - t.entry_time).days, 1)
        total_pnl_pct += t.pnl_pct
        print(f"  {t.signal_source:<12} entry=${t.entry_price:.2f} exit=${t.exit_price:.2f} "
              f"pnl={t.pnl_pct:+.2%} dur={dur}d  (cumulative: {total_pnl_pct:+.2%})")

    # Price path
    prices = [x["price"] for x in h]
    print(f"\nKey price points:")
    for i in [0, 20, 40, 60, 80, 100, 120, 140, 160, 180, 200, 220, 251]:
        if i < len(prices):
            print(f"  bar={i:<4} ${prices[i]:.2f}")

asyncio.run(main())
