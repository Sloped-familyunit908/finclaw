"""Debug V-Recovery scenario"""
import asyncio, random, math
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.backtester_v7 import BacktesterV7

def sim(start, days, ret, vol, seed=42, jp=0.05, js=0.10):
    rng = random.Random(seed); dt = 1/252; prices = [start]
    for _ in range(days-1):
        dW = rng.gauss(0, math.sqrt(dt))
        j = rng.gauss(0,js) if rng.random() < jp else 0
        prices.append(max(prices[-1] * math.exp((ret-0.5*vol**2)*dt + vol*dW + j), 0.01))
    base = datetime(2025,3,1)
    return [{'date': base+timedelta(days=i), 'price': p,
             'volume': abs(rng.gauss(p*1e6, p*5e5))} for i,p in enumerate(prices)]

async def main():
    h = sim(200, 252, 0.40, 0.60, 5002, 0.05, 0.10)
    bh = h[-1]["price"] / h[0]["price"] - 1
    bt = BacktesterV7(initial_capital=10000)
    r = await bt.run("V", "v7", h)
    print(f"V-Recovery: B&H={bh:+.1%}  ret={r.total_return:+.1%}  alpha={r.total_return-bh:+.1%}")
    print(f"trades={r.total_trades} WR={r.win_rate:.0%}")
    for t in r.trades:
        dur = (t.exit_time - t.entry_time).days
        print(f"  {t.signal_source:<12} entry=${t.entry_price:.1f} exit=${t.exit_price:.1f} "
              f"pnl={t.pnl_pct:+.1%} dur={dur}d")

    # Show price path
    prices = [x["price"] for x in h]
    print(f"\nPrice path (every 20 bars):")
    for i in range(0, len(prices), 20):
        print(f"  bar={i:<4} ${prices[i]:.1f}")

asyncio.run(main())
