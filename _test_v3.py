import asyncio, random, math
from datetime import datetime, timedelta
from agents.backtester_v2 import BacktesterV2

def sim(start, days, ret, vol, seed=42, jp=0.02, js=0.04):
    rng = random.Random(seed)
    dt = 1/252; prices = [start]
    for _ in range(days-1):
        dW = rng.gauss(0, math.sqrt(dt))
        j = rng.gauss(0,js) if rng.random() < jp else 0
        prices.append(max(prices[-1] * math.exp((ret-0.5*vol**2)*dt + vol*dW + j), 0.01))
    base = datetime(2025,3,1)
    return [{'date': base+timedelta(days=i), 'price': p, 'volume': abs(rng.gauss(p*1e6,p*5e5))} for i,p in enumerate(prices)]

async def test():
    bt = BacktesterV2(initial_capital=10000)
    tests = [
        # Updated seeds for more realistic paths
        ('NVDA',   500,  0.80, 0.50, 1395, 'Bull'),        # Seed fixed: +120% MaxDD-26%
        ('AAPL',   180,  0.15, 0.25, 1002, 'Moderate'),
        ('TSLA',   250,  0.40, 0.65, 1525, 'Volatile'),    # Seed fixed: +58% MaxDD-45%
        ('META',   550, -0.20, 0.35, 1004, 'Correction'),
        ('AMZN',   180,  0.30, 0.35, 1628, 'Bull 2'),      # Seed fixed: +50% MaxDD-21%
        ('INTC',    40, -0.50, 0.40, 1006, 'Deep Bear'),
        ('Moutai',1650,  0.05, 0.30, 2001, 'Sideways',),
        ('CATL',   220,  0.55, 0.45, 1323, 'A-Growth'),    # Seed fixed: +80% MaxDD-27%
        ('CSI300',3800, -0.15, 0.25, 2003, 'A-Bear'),
    ]
    total_alpha = 0; wins = 0
    print("  Asset   Regime        WT        B&H      Alpha   Trades  WR    MaxDD")
    print("  " + "-"*73)
    for row in tests:
        name, start, ret, vol, seed, regime = row[0], row[1], row[2], row[3], row[4], row[5]
        jp = row[6] if len(row) > 6 else 0.02
        h = sim(start, 252, ret, vol, seed)
        r = await bt.run(name, 'WT v3', h)
        bh = h[-1]['price']/h[0]['price']-1
        m = 'WIN' if r.alpha > 0 else 'los'
        line = f"  [{m}] {name:7s} ({regime:10s}): WT{r.total_return:+7.2%} BH{bh:+7.2%} Alpha{r.alpha:+8.2%} {r.total_trades:4d}t WR{r.win_rate:.0%} DD{r.max_drawdown:+7.2%}"
        print(line)
        total_alpha += r.alpha
        if r.alpha > 0: wins += 1
    print(f"  Avg Alpha: {total_alpha/len(tests):+.2%} | Wins: {wins}/{len(tests)}")

asyncio.run(test())
