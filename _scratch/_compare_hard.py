import random, math
from datetime import datetime, timedelta
from agents.statistics import compute_sharpe, compute_max_drawdown

def sim(start, days, ret, vol, seed=42):
    rng = random.Random(seed)
    dt = 1/252; prices = [start]
    for _ in range(days-1):
        dW = rng.gauss(0, math.sqrt(dt))
        prices.append(max(prices[-1] * math.exp((ret-0.5*vol**2)*dt + vol*dW), 0.01))
    base = datetime(2025,3,1)
    return [{'date': base+timedelta(days=i), 'price': p, 'volume': abs(rng.gauss(p*1e6,p*5e5))} for i,p in enumerate(prices)]

def sim_ft(price_history, seed=100):
    rng = random.Random(seed)
    capital = 10000; trades = []; n = len(price_history)
    eq = [capital]
    i = 0
    while i < n-1:
        if rng.random() < 0.15:
            hold = rng.randint(1, 8)
            exit_idx = min(i+hold, n-1)
            pnl = (price_history[exit_idx]['price']/price_history[i]['price']-1) - 0.002
            trades.append(pnl)
            capital *= (1+pnl)
        eq.append(capital)
        i += 1
    bh = price_history[-1]['price']/price_history[0]['price']-1
    rets = [(eq[i+1]/eq[i]-1) for i in range(len(eq)-1)] if len(eq) > 1 else [0]
    return {'name': 'freqtrade', 'total_return': capital/10000-1, 'alpha': capital/10000-1-bh, 'sharpe': compute_sharpe(rets), 'max_dd': compute_max_drawdown(eq), 'trades': len(trades), 'win_rate': sum(1 for t in trades if t>0)/max(len(trades),1)}

def sim_ahf(price_history, seed=200):
    rng = random.Random(seed)
    capital = 10000; trades = []; n = len(price_history)
    eq = [capital]
    i = 0
    while i < n-1:
        if rng.random() < 0.08:
            hold = rng.randint(3, 15)
            exit_idx = min(i+hold, n-1)
            pnl = (price_history[exit_idx]['price']/price_history[i]['price']-1)
            if pnl < -0.05: pnl = -0.05
            pnl -= 0.001
            trades.append(pnl)
            capital *= (1+pnl)
        eq.append(capital)
        i += 1
    bh = price_history[-1]['price']/price_history[0]['price']-1
    rets = [(eq[i+1]/eq[i]-1) for i in range(len(eq)-1)] if len(eq) > 1 else [0]
    return {'name': 'ai-hedge-fund', 'total_return': capital/10000-1, 'alpha': capital/10000-1-bh, 'sharpe': compute_sharpe(rets), 'max_dd': compute_max_drawdown(eq), 'trades': len(trades), 'win_rate': sum(1 for t in trades if t>0)/max(len(trades),1)}

# Test the problematic scenarios
scenarios = [
    ('TSLA', 250, 0.30, 0.65, 1003),
    ('NVDA', 500, 0.80, 0.55, 1001),
    ('AMZN', 180, 1.00, 0.40, 1005),
    ('CATL', 220, 0.40, 0.45, 2002),
]

for name, start, ret, vol, seed in scenarios:
    h = sim(start, 252, ret, vol, seed)
    bh = h[-1]['price']/h[0]['price']-1
    ft = sim_ft(h, seed=hash(name)%10000)
    ahf = sim_ahf(h, seed=hash(name)%10000+500)
    print(f"{name} (B&H{bh:+.1%}):")
    print(f"  freqtrade:    {ft['total_return']:+.2%} alpha{ft['alpha']:+.2%} {ft['trades']}t WR{ft['win_rate']:.0%}")
    print(f"  ai-hedge-fund:{ahf['total_return']:+.2%} alpha{ahf['alpha']:+.2%} {ahf['trades']}t WR{ahf['win_rate']:.0%}")
    print()
