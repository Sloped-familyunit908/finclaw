"""Trace exact Moutai entry logic"""
import asyncio, random, math
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.signal_engine_v7 import SignalEngineV7, MarketRegime

def sim(start, days, ret, vol, seed=42, jp=0.03, js=0.06):
    rng = random.Random(seed); dt = 1/252; prices = [start]
    for _ in range(days-1):
        dW = rng.gauss(0, math.sqrt(dt))
        j = rng.gauss(0,js) if rng.random() < jp else 0
        prices.append(max(prices[-1] * math.exp((ret-0.5*vol**2)*dt + vol*dW + j), 0.01))
    return [{'date': datetime(2025,3,1)+timedelta(days=i), 'price': p} for i,p in enumerate(prices)]

async def main():
    h = sim(1650, 252, 0.05, 0.30, 2001, 0.03, 0.06)
    prices = [x["price"] for x in h]
    engine = SignalEngineV7()
    warmup = 20
    capital = 10000
    position = None
    last_exit_idx = None
    cooldown = 0

    print("Simulating Moutai bars 0-50:")
    for i in range(0, 55):
        price = prices[i]

        if position is not None:
            pnl_pct = price / position["entry"] - 1
            # Check exit
            if pnl_pct < -0.06 or (i > position["entry_bar"] + 1 and pnl_pct < -0.03):
                print(f"  bar={i} EXIT price=${price:.0f} pnl={pnl_pct:+.1%}")
                last_exit_idx = i
                position = None
                cooldown = 1
                continue

        if cooldown > 0:
            print(f"  bar={i} COOLDOWN remaining={cooldown}")
            cooldown -= 1
            continue

        if i < warmup:
            continue

        sig = engine.generate_signal(prices[:i+1], current_position=1.0 if position else 0)
        bars_since = i - (last_exit_idx if last_exit_idx else warmup)
        ft = 6 if sig.regime in (MarketRegime.BULL, MarketRegime.STRONG_BULL, MarketRegime.VOLATILE) else 12
        force = bars_since > ft

        if position is None:
            should = (sig.signal in ("buy","strong_buy") and sig.confidence > 0.35) or force
            print(f"  bar={i} price=${price:.0f} regime={sig.regime.value:<12} sig={sig.signal:<10} "
                  f"conf={sig.confidence:.2f} bars_since={bars_since} ft={ft} force={force} enter={should}")
            if should:
                position = {"entry": price, "entry_bar": i, "size": sig.position_size}
                print(f"    >> ENTERED pos_size={sig.position_size:.2f}")
                if i > 35: break

asyncio.run(main())
