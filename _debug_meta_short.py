"""Debug META in v7+ to find the bug"""
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
    h = sim(550, 252, -0.20, 0.35, 1004)
    # v7
    bt7 = BacktesterV7(initial_capital=10000)
    r7 = await bt7.run("META", "v7", h)
    print(f"v7: ret={r7.total_return:+.1%} trades={r7.total_trades}")
    for t in r7.trades:
        print(f"  [{t.side}] {t.signal_source:<12} entry={t.entry_price:.0f} exit={t.exit_price:.0f} pnl={t.pnl_pct:+.2%}")

    print()
    # v7+
    bt7p = BacktesterV7Plus(initial_capital=10000, enable_short=True)
    r7p = await bt7p.run("META", "v7+", h)
    print(f"v7+: ret={r7p.total_return:+.1%} trades={r7p.total_trades}")
    for t in r7p.trades:
        print(f"  [{t.side}] {t.signal_source:<12} entry={t.entry_price:.0f} exit={t.exit_price:.0f} pnl={t.pnl_pct:+.2%}")

asyncio.run(main())
