import asyncio, random, math
from datetime import datetime, timedelta
from agents.backtester_v2 import BacktesterV2
from agents.backtester_v3 import AIBacktester

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
    tests = [
        ('NVDA',   500,  0.80, 0.50, 1395, 'Bull'),
        ('AAPL',   180,  0.15, 0.25, 1002, 'Moderate'),
        ('TSLA',   250,  0.40, 0.65, 1525, 'Volatile'),
        ('META',   550, -0.20, 0.35, 1004, 'Correction'),
        ('AMZN',   180,  0.30, 0.35, 1628, 'Bull 2'),
        ('INTC',    40, -0.50, 0.40, 1006, 'Deep Bear'),
        ('Moutai',1650,  0.05, 0.30, 2001, 'Sideways'),
        ('CATL',   220,  0.55, 0.45, 1323, 'A-Growth'),
        ('CSI300',3800, -0.15, 0.25, 2003, 'A-Bear'),
    ]
    
    total_rules = 0; total_ai = 0; wr = 0; wa = 0
    
    print("  Asset   Regime        Rules    AI+Rules  Improvement")
    print("  " + "-"*60)
    
    for name, start, ret, vol, seed, regime in tests:
        h = sim(start, 252, ret, vol, seed)
        
        bt1 = BacktesterV2(initial_capital=10000)
        r1 = await bt1.run(name, 'Rules', h)
        
        bt2 = AIBacktester(initial_capital=10000, use_ai=True, ai_budget=15)
        r2 = await bt2.run(name, 'AI', h)
        
        imp = r2.alpha - r1.alpha
        m = 'UP' if imp > 0.001 else ('dn' if imp < -0.001 else '==')
        
        print(f"  [{m}] {name:7s} ({regime:10s}): {r1.alpha:>+7.2%}  {r2.alpha:>+7.2%}  {imp:>+7.2%}")
        total_rules += r1.alpha; total_ai += r2.alpha
        if r1.alpha > 0: wr += 1
        if r2.alpha > 0: wa += 1
    
    n = len(tests)
    print(f"\n  Rules:    avg alpha {total_rules/n:+.2%} | {wr}/{n} wins")
    print(f"  AI+Rules: avg alpha {total_ai/n:+.2%} | {wa}/{n} wins")
    print(f"  Delta:    {(total_ai-total_rules)/n:+.2%}")

asyncio.run(test())
