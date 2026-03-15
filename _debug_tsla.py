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

async def debug_tsla():
    bt = BacktesterV2(initial_capital=10000)
    h = sim(250, 252, 0.30, 0.65, 1003)
    prices = [x['price'] for x in h]
    print(f"TSLA path: {prices[0]:.0f} -> {prices[-1]:.0f} ({prices[-1]/prices[0]-1:+.1%})")
    
    r = await bt.run('TSLA', 'WT v3', h)
    bh = h[-1]['price']/h[0]['price']-1
    print(f"Result: WT{r.total_return:+.2%} B&H{bh:+.2%} Alpha{r.alpha:+.2%} {r.total_trades} trades")
    
    # Show trade details
    print("\nTrade log:")
    for i, t in enumerate(r.trades):
        print(f"  {i+1}. {t.signal_source:15s} entry=${t.entry_price:.0f} exit=${t.exit_price:.0f} pnl={t.pnl_pct:+.2%}")
    
    # Check signals at key bars
    se = SignalEngine()
    print("\nSignals at key bars:")
    for bar in [55, 75, 100, 125, 150, 175, 200]:
        sig = se.generate_signal(prices[:bar+1])
        print(f"  Bar {bar}: ${prices[bar]:.0f} -> {sig.signal:12s} conf={sig.confidence:.2f} regime={sig.regime.value:12s} ADX-approx")

asyncio.run(debug_tsla())
