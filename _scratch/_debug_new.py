"""Debug new scenarios: MSFT, BABA, GOLD"""
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
    cases = [
        ("MSFT (Steady)", sim(410, 252, 0.12, 0.22, 3001)),
        ("BABA (Deep Bear)", sim(80, 252, -0.35, 0.45, 3002, 0.03, 0.06)),
        ("GOLD (LowVol)", sim(2000, 252, 0.08, 0.15, 3003)),
    ]
    for name, h in cases:
        bh = h[-1]["price"] / h[0]["price"] - 1
        bt = BacktesterV7(initial_capital=10000)
        r = await bt.run("T", "v7", h)
        alpha = r.total_return - bh
        print(f"\n{name}  B&H={bh:+.1%}  ret={r.total_return:+.1%}  alpha={alpha:+.1%}")
        print(f"  trades={r.total_trades} WR={r.win_rate:.0%} MaxDD={r.max_drawdown:.1%}")
        for t in r.trades:
            dur = (t.exit_time - t.entry_time).days
            print(f"  {t.signal_source:<12} entry=${t.entry_price:.2f} exit=${t.exit_price:.2f} "
                  f"pnl={t.pnl_pct:+.1%} dur={dur}d")

asyncio.run(main())
