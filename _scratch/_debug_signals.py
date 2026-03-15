import random, math
from agents.signal_engine import SignalEngine

def sim(start, days, ret, vol, seed=42):
    rng = random.Random(seed)
    dt = 1/252; prices = [start]
    for _ in range(days-1):
        dW = rng.gauss(0, math.sqrt(dt))
        prices.append(max(prices[-1] * math.exp((ret-0.5*vol**2)*dt + vol*dW), 0.01))
    return prices

se = SignalEngine()
prices = sim(500, 252, 0.80, 0.55, 1001)

buy_count = sell_count = hold_count = 0
for i in range(50, len(prices), 5):
    sig = se.generate_signal(prices[:i+1])
    if sig.signal in ('buy', 'strong_buy'): buy_count += 1
    elif sig.signal in ('sell', 'strong_sell'): sell_count += 1
    else: hold_count += 1

print(f"NVDA Bull: {buy_count} buys, {sell_count} sells, {hold_count} holds")
print(f"Buy ratio: {buy_count/(buy_count+sell_count+hold_count):.1%}")

for i in [60, 100, 150, 200]:
    sig = se.generate_signal(prices[:i+1])
    price_chg = (prices[i]/prices[50]-1)*100
    print(f"  Bar {i}: price {prices[i]:.0f} ({price_chg:+.0f}%) -> {sig.signal} conf={sig.confidence:.2f} regime={sig.regime.value}")
    for k, v in sig.factors.items():
        print(f"    {k}: {v:+.3f}")
