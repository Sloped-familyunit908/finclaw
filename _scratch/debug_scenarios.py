import asyncio, random, math
from datetime import datetime, timedelta
import sys; sys.path.insert(0,'.')
from agents.backtester_v4 import BacktesterV4

def sim(start, days, ret, vol, seed=42, jp=0.02, js=0.04):
    rng = random.Random(seed)
    dt = 1/252; prices = [start]
    for _ in range(days-1):
        dW = rng.gauss(0, math.sqrt(dt))
        j = rng.gauss(0,js) if rng.random() < jp else 0
        prices.append(max(prices[-1] * math.exp((ret-0.5*vol**2)*dt + vol*dW + j), 0.01))
    base = datetime(2025,3,1)
    return [{'date': base+timedelta(days=i), 'price': p, 'volume': abs(rng.gauss(p*1e6, p*5e5))} for i,p in enumerate(prices)]

async def debug(name, *args):
    ph = sim(*args)
    bh = ph[-1]['price']/ph[0]['price']-1
    print(f'\n{name} B&H={bh:.1%}  start={ph[0]["price"]:.2f}  end={ph[-1]["price"]:.2f}')
    bt = BacktesterV4()
    r = await bt.run(name,'debug',ph)
    print(f'WT return={r.total_return:.1%}  alpha={r.alpha:.1%}  trades={r.total_trades}')
    for t in r.trades:
        dur = (t.exit_time - t.entry_time).days
        print(f'  {t.signal_source:<18} buy@{t.entry_price:.2f} sell@{t.exit_price:.2f}  pnl={t.pnl_pct:+.1%}  dur={dur}d')

async def main():
    await debug('AAPL', 210, 252, -0.20, 0.30, 2847)
    await debug('BTC',  83972, 365, -0.10, 0.60, 9999)

asyncio.run(main())
