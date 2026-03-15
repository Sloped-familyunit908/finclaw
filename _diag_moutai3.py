"""Debug Moutai position sizing"""
import asyncio, random, math
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.signal_engine_v7 import SignalEngineV7

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
    last_exit = warmup

    print("Tracing Moutai bars 20-55 (looking for force_entry point):")
    for i in range(warmup, 60):
        bars_since = i - last_exit
        sig = engine.generate_signal(prices[:i+1], current_position=0)
        if bars_since > 12 or sig.signal in ("buy","strong_buy"):
            print(f"  bar={i} price=${prices[i]:.0f} regime={sig.regime.value:<12} "
                  f"signal={sig.signal:<10} pos_size={sig.position_size:.2f} "
                  f"bars_since={bars_since} ** WOULD ENTER")
            if bars_since > 12:
                print(f"    >> force_entry at pos_size={sig.position_size:.2f}")
            break
        print(f"  bar={i} price=${prices[i]:.0f} regime={sig.regime.value:<12} "
              f"signal={sig.signal:<10} pos_size={sig.position_size:.2f} bars_since={bars_since}")

    # Simulate simple position:
    # entry at bar 36 with pos_size=0.40 vs pos_size=0.80
    entry_bar = 36
    entry_price = prices[entry_bar]
    exit_price = prices[-1]
    bh = exit_price / prices[0] - 1
    for ps in [0.40, 0.50, 0.60, 0.70, 0.80, 0.92]:
        gain = ps * (exit_price / entry_price - 1)
        first_loss = 0.40 * (prices[2] / prices[0] - 1) * 0.45  # approximate
        total = gain
        print(f"  pos_size={ps:.2f}: gain={gain:+.1%} (vs B&H={bh:+.1%})")

asyncio.run(main())
