import random, math, sys
sys.path.insert(0,'.')
from agents.signal_engine_v5 import SignalEngineV5

def sim(start, days, ret, vol, seed):
    rng = random.Random(seed)
    dt = 1/252; prices = [start]
    for _ in range(days-1):
        dW = rng.gauss(0, math.sqrt(dt))
        j = rng.gauss(0,0.04) if rng.random() < 0.02 else 0
        prices.append(max(prices[-1]*math.exp((ret-0.5*vol**2)*dt+vol*dW+j), 0.01))
    return prices

prices = sim(250, 365, -0.50, 0.70, 5555)
engine = SignalEngineV5()
print('TSLA Signal Trace')
print(f'{"Bar":>4} {"Price":>8} {"chg5":>6} {"Regime":>14} {"Signal":>10} {"Conf":>6}')
prev_regime = None
for i in range(10, 50):
    sig = engine.generate_signal(prices[:i+1])
    r_str = sig.regime.value if sig.regime != prev_regime else '...'
    prev_regime = sig.regime
    chg5 = prices[i]/prices[max(0,i-5)]-1 if i>=5 else 0
    print(f'{i:4d} {prices[i]:8.2f} {chg5:+5.1%} {r_str:>14} {sig.signal:>10} {sig.confidence:.2f}')
print(f'Final price: {prices[-1]:.2f}  B&H: {prices[-1]/prices[0]-1:+.1%}')
