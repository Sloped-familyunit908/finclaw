"""
Stress test v7 with EXTREME scenarios.
Find edge cases where the engine breaks.
"""
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
    stress = [
        # Extreme bull
        ("MEGA Bull",      sim(100, 252, 1.50, 0.30, 5001)),
        # V-recovery
        ("V-Recovery",     sim(200, 252, 0.40, 0.60, 5002, 0.05, 0.10)),
        # Slow bleed
        ("Slow Bleed",     sim(100, 252,-0.30, 0.15, 5003)),
        # Flash crash + recovery
        ("Flash Crash",    sim(500, 252, 0.10, 0.80, 5004, 0.08, 0.15)),
        # Flat then rocket
        ("Flat->Rocket",   sim(50, 252, 0.60, 0.20, 5005)),
        # Pump and dump
        ("Pump&Dump",      sim(10, 252,-0.20, 0.90, 5006, 0.10, 0.20)),
        # Steady dividend style
        ("Dividend",       sim(100, 252, 0.08, 0.12, 5007)),
        # Mean revert oscillator
        ("Oscillator",     sim(100, 252, 0.00, 0.35, 5008)),
        # Parabolic then crash
        ("Parabolic",      sim(100, 252, 2.00, 0.50, 5009, 0.05, 0.08)),
        # Double bottom
        ("Double Bottom",  sim(200, 252, 0.05, 0.45, 5010, 0.04, 0.08)),
    ]

    print(f"{'Scenario':<16} {'B&H':>7} {'v7_ret':>7} {'alpha':>7} | {'#T':>3} {'WR':>4} {'MaxDD':>7}")
    print("-"*65)

    alphas = []
    for name, h in stress:
        bh = h[-1]["price"]/h[0]["price"]-1
        bt = BacktesterV7(initial_capital=10000)
        r = await bt.run(name, "v7", h)
        a = r.total_return - bh
        alphas.append(a)
        tag = "+" if a > 0.05 else ("-" if a < -0.05 else "=")
        print(f"[{tag}] {name:<14} {bh:>+6.1%} {r.total_return:>+6.1%} {a:>+6.1%} | "
              f"{r.total_trades:>3} {r.win_rate:>3.0%} {r.max_drawdown:>+6.1%}")

    avg_a = sum(alphas)/len(alphas)
    pos = sum(1 for a in alphas if a > 0)
    print(f"\nAvg alpha: {avg_a:+.1%} | Positive: {pos}/{len(alphas)}")

asyncio.run(main())
