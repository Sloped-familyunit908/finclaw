import asyncio, random, math
from datetime import datetime, timedelta
from agents.backtester_v2 import BacktesterV2
from agents.signal_engine import SignalEngine

def sim(start, days, ret, vol, seed=42):
    rng = random.Random(seed)
    dt = 1/252; prices = [start]
    for _ in range(days-1):
        dW = rng.gauss(0, math.sqrt(dt))
        prices.append(max(prices[-1] * math.exp((ret-0.5*vol**2)*dt + vol*dW), 0.01))
    base = datetime(2025,3,1)
    return [{'date': base+timedelta(days=i), 'price': p, 'volume': abs(rng.gauss(p*1e6,p*5e5))} for i,p in enumerate(prices)]

async def debug():
    bt = BacktesterV2(initial_capital=10000)
    
    for name, start, ret, vol, seed in [('NVDA', 500, 0.80, 0.50, 1395), ('CATL', 220, 0.55, 0.45, 1323)]:
        h = sim(start, 252, ret, vol, seed)
        prices = [x['price'] for x in h]
        bh = h[-1]['price']/h[0]['price']-1
        
        r = await bt.run(name, 'WT v4', h)
        print(f"\n{'='*60}")
        print(f"{name}: WT{r.total_return:+.2%} B&H{bh:+.2%} Alpha{r.alpha:+.2%} {r.total_trades} trades")
        print(f"{'='*60}")
        
        for i, t in enumerate(r.trades):
            dur = (t.exit_time - t.entry_time).days if isinstance(t.entry_time, datetime) else 0
            print(f"  {i+1:2d}. {t.signal_source:15s} entry=${t.entry_price:.0f} exit=${t.exit_price:.0f} pnl={t.pnl_pct:+.2%} {dur}d")
        
        # Check what regimes were detected at various bars
        se = SignalEngine()
        print(f"\n  Regime detection at key bars:")
        for bar in [55, 75, 100, 125, 150, 175, 200, 230]:
            if bar < len(prices):
                sig = se.generate_signal(prices[:bar+1])
                print(f"    Bar {bar:3d}: ${prices[bar]:.0f} ({prices[bar]/prices[0]-1:+.0%}) regime={sig.regime.value:12s} signal={sig.signal:12s} conf={sig.confidence:.2f}")

asyncio.run(debug())
