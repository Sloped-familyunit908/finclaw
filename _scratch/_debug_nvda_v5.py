"""Debug NVDA bull scenario with v5 engine — trace every trade."""
import asyncio, random, math
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.backtester_v4 import BacktesterV4

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
    h = sim(500, 252, 0.80, 0.50, 1395)
    bh = h[-1]["price"]/h[0]["price"]-1
    print(f"NVDA: ${h[0]['price']:.0f} -> ${h[-1]['price']:.0f} (B&H: {bh:+.1%})")
    print(f"High: ${max(b['price'] for b in h):.0f}, Low: ${min(b['price'] for b in h):.0f}")
    
    # Show price at key intervals
    print("\nPrice path (every 25 bars):")
    for i in range(0, len(h), 25):
        p = h[i]["price"]
        ret = p/h[0]["price"]-1
        print(f"  Bar {i:3d}: ${p:8.2f} ({ret:+.1%})")
    
    bt = BacktesterV4(initial_capital=10000)
    r = await bt.run("NVDA","WT v5",h)
    
    print(f"\nTotal return: {r.total_return:+.1%}")
    print(f"Alpha: {r.total_return - bh:+.1%}")
    print(f"Total trades: {r.total_trades}")
    print(f"MaxDD: {r.max_drawdown:.1%}")
    print(f"Win rate: {r.win_rate:.0%}")
    
    print(f"\nTRADE DETAILS:")
    for i, t in enumerate(r.trades):
        print(f"  #{i+1}: entry=${t.entry_price:.2f} exit=${t.exit_price:.2f} "
              f"pnl={t.pnl_pct:+.1%} reason={t.signal_source} "
              f"dur={(t.exit_time-t.entry_time).days}d")

asyncio.run(main())
