"""Moutai deep analysis - why still -14%?"""
import asyncio, random, math
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.backtester_v7 import BacktesterV7
from agents.signal_engine_v7 import SignalEngineV7, MarketRegime

def sim(start, days, ret, vol, seed=42, jp=0.03, js=0.06):
    rng = random.Random(seed); dt = 1/252; prices = [start]
    for _ in range(days-1):
        dW = rng.gauss(0, math.sqrt(dt))
        j = rng.gauss(0, js) if rng.random() < jp else 0
        prices.append(max(prices[-1]*math.exp((ret-0.5*vol**2)*dt+vol*dW+j), 0.01))
    base = datetime(2025,3,1)
    return [{'date':base+timedelta(days=i),'price':p,
             'volume':abs(random.Random(seed+i).gauss(p*1e6,p*5e5))} for i,p in enumerate(prices)]

async def main():
    h = sim(1650, 252, 0.05, 0.30, 2001, 0.03, 0.06)
    bh = h[-1]["price"]/h[0]["price"]-1
    bt = BacktesterV7(initial_capital=10000)
    r = await bt.run("Moutai", "v7", h)
    print(f"Moutai: B&H={bh:+.1%}  v7={r.total_return:+.1%}  alpha={r.total_return-bh:+.1%}")
    print(f"trades={r.total_trades}  WR={r.win_rate:.0%}  MaxDD={r.max_drawdown:+.1%}")
    print(f"\nTrades:")
    equity = 10000
    for t in r.trades:
        dur = max((t.exit_time - t.entry_time).days, 1)
        print(f"  {t.signal_source:<12} entry=${t.entry_price:.0f} exit=${t.exit_price:.0f} "
              f"pnl={t.pnl_pct:+.2%} pnl$=${t.pnl:+.0f} dur={dur}d")

    prices = [x["price"] for x in h]
    print(f"\nPrice path:")
    for i in [0,20,40,60,80,100,120,140,160,180,200,220,240,251]:
        if i < len(prices): print(f"  bar={i:<4} ${prices[i]:.0f}")

    print(f"\nRegime trace (every 10 bars):")
    engine = SignalEngineV7()
    for i in range(20, len(prices), 10):
        p = prices[:i+1]
        v = [x.get("volume",0) for x in h[:i+1]]
        sig = engine.generate_signal(p, v)
        print(f"  bar={i:<4} ${prices[i]:.0f} {sig.regime.value:<14} {sig.signal}")

asyncio.run(main())
