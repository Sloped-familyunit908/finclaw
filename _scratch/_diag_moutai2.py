"""Diagnose Moutai — why do we miss 14% alpha?"""
import asyncio, random, math
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.backtester_v7 import BacktesterV7
from agents.signal_engine_v7 import SignalEngineV7

def sim(start, days, ret, vol, seed=42, jp=0.03, js=0.06):
    rng = random.Random(seed); dt = 1/252; prices = [start]
    for _ in range(days-1):
        dW = rng.gauss(0, math.sqrt(dt))
        j = rng.gauss(0,js) if rng.random() < jp else 0
        prices.append(max(prices[-1] * math.exp((ret-0.5*vol**2)*dt + vol*dW + j), 0.01))
    base = datetime(2025,3,1)
    return [{'date': base+timedelta(days=i), 'price': p,
             'volume': abs(rng.gauss(p*1e6, p*5e5))} for i,p in enumerate(prices)]

async def main():
    h = sim(1650, 252, 0.05, 0.30, 2001, 0.03, 0.06)
    bh = h[-1]["price"] / h[0]["price"] - 1
    bt = BacktesterV7(initial_capital=10000)
    r = await bt.run("Moutai", "v7", h)
    alpha = r.total_return - bh
    prices = [x["price"] for x in h]

    print(f"Moutai: B&H={bh:+.1%}  ret={r.total_return:+.1%}  alpha={alpha:+.1%}")
    print(f"trades={r.total_trades}  WR={r.win_rate:.0%}  MaxDD={r.max_drawdown:.1%}")
    print()

    # Show trade timeline + regime
    engine = SignalEngineV7()
    print(f"  {'#':<3} {'Reason':<12} {'Entry':>8} {'Exit':>8} {'PnL':>7} {'Dur':>5}  Regime@entry")
    total_in_market = 0
    for i, t in enumerate(r.trades):
        dur = (t.exit_time - t.entry_time).days
        total_in_market += dur
        print(f"  {i+1:<3} {t.signal_source:<12} ${t.entry_price:>7.0f} ${t.exit_price:>7.0f} "
              f"{t.pnl_pct:>+6.1%} {dur:>5}d")

    print(f"\nTotal in market: {total_in_market} days out of {len(h)} ({total_in_market/len(h):.0%})")
    print(f"Missed B&H: {bh - r.total_return:+.1%}")

    # Analyze where we are NOT in market and what prices did
    print("\n--- Period analysis (every 30 bars) ---")
    engine2 = SignalEngineV7()
    warmup = 20
    for i in range(warmup, len(h), 30):
        sig = engine2.generate_signal(
            prices[:i+1],
            current_position=0,
        )
        p_now = prices[i]
        p_30 = prices[min(i+30, len(h)-1)]
        fwd = p_30 / p_now - 1
        print(f"  bar={i:<4} price={p_now:>8.0f} regime={sig.regime.value:<12} signal={sig.signal:<10} fwd30={fwd:+.1%}")

asyncio.run(main())
