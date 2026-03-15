"""Debug AAPL — we're 0.8% behind AHF"""
import asyncio, random, math
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.backtester_v7 import BacktesterV7

def sim(start, days, ret, vol, seed=42, jp=0.02, js=0.04):
    rng = random.Random(seed); dt = 1/252; prices = [start]
    for _ in range(days-1):
        dW = rng.gauss(0, math.sqrt(dt))
        j = rng.gauss(0,js) if rng.random() < jp else 0
        prices.append(max(prices[-1] * math.exp((ret-0.5*vol**2)*dt + vol*dW + j), 0.01))
    base = datetime(2025,3,1)
    return [{'date': base+timedelta(days=i), 'price': p,
             'volume': abs(rng.gauss(p*1e6, p*5e5))} for i,p in enumerate(prices)]

async def main():
    h = sim(180, 252, 0.15, 0.25, 1002)  # AAPL: moderate decline
    bh = h[-1]["price"] / h[0]["price"] - 1
    bt = BacktesterV7(initial_capital=10000)
    r = await bt.run("AAPL", "v7", h)
    alpha = r.total_return - bh
    print(f"AAPL: B&H={bh:+.1%}  ret={r.total_return:+.1%}  alpha={alpha:+.1%}")
    print(f"trades={r.total_trades}  WR={r.win_rate:.0%}  MaxDD={r.max_drawdown:.1%}")
    print()
    total_in_mkt = 0
    for t in r.trades:
        dur = (t.exit_time - t.entry_time).days
        total_in_mkt += dur
        print(f"  {t.signal_source:<12} entry=${t.entry_price:.2f} exit=${t.exit_price:.2f} "
              f"pnl={t.pnl_pct:+.1%} dur={dur}d")
    print(f"\nTotal in market: {total_in_mkt}d / {len(h)}d ({total_in_mkt/len(h):.0%})")

asyncio.run(main())
