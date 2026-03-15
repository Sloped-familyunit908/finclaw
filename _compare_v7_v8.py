"""Compare v7 vs v8 on all scenarios side-by-side with same data"""
import asyncio, random, math, statistics, aiohttp
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.backtester_v7 import BacktesterV7
from agents.backtester_v8 import BacktesterV8

def sim(start, days, ret, vol, seed=42, jp=0.02, js=0.04):
    rng = random.Random(seed); dt = 1/252; prices = [start]
    for _ in range(days-1):
        dW = rng.gauss(0, math.sqrt(dt))
        j = rng.gauss(0,js) if rng.random() < jp else 0
        prices.append(max(prices[-1] * math.exp((ret-0.5*vol**2)*dt + vol*dW + j), 0.01))
    base = datetime(2025,3,1)
    return [{'date': base+timedelta(days=i), 'price': p,
             'volume': abs(rng.gauss(p*1e6, p*5e5))} for i,p in enumerate(prices)]

async def fetch_crypto(asset, days=365):
    coin = {"BTC":"bitcoin","ETH":"ethereum","SOL":"solana"}[asset]
    url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart"
    async with aiohttp.ClientSession() as s:
        async with s.get(url, params={"vs_currency":"usd","days":str(days)}) as r:
            data = await r.json()
    hist = [{"date":datetime.fromtimestamp(ts/1000),"price":p} for ts,p in data.get("prices",[])]
    for i,(ts,v) in enumerate(data.get("total_volumes",[])):
        if i < len(hist): hist[i]["volume"] = v
    return hist

async def main():
    scenarios = [
        ("NVDA",    sim(500, 252, 0.80, 0.50, 1395)),
        ("AAPL",    sim(180, 252, 0.15, 0.25, 1002)),
        ("TSLA",    sim(250, 252, 0.40, 0.65, 1525)),
        ("META",    sim(550, 252,-0.20, 0.35, 1004)),
        ("AMZN",    sim(180, 252, 0.30, 0.35, 1628)),
        ("INTC",    sim(40,  252,-0.50, 0.40, 1006)),
        ("Moutai",  sim(1650,252, 0.05, 0.30, 2001, 0.03, 0.06)),
        ("CATL",    sim(220, 252, 0.55, 0.45, 1323, 0.03, 0.06)),
        ("CSI300",  sim(3800,252,-0.15, 0.25, 2003, 0.03, 0.06)),
    ]
    for asset in ["BTC","ETH","SOL"]:
        h = await fetch_crypto(asset, 365)
        scenarios.append((asset, h))
        await asyncio.sleep(5)

    print(f"  {'Scenario':<12} {'B&H':>7} | {'v7 alpha':>10} {'v8 alpha':>10} | {'delta':>7} | winner")
    print("  " + "-"*65)

    v7_alphas = []; v8_alphas = []
    for name, h in scenarios:
        bh = h[-1]["price"] / h[0]["price"] - 1
        bt7 = BacktesterV7(initial_capital=10000)
        bt8 = BacktesterV8(initial_capital=10000)
        r7 = await bt7.run("T","v7",h)
        r8 = await bt8.run("T","v8",h)
        a7 = r7.total_return - bh; a8 = r8.total_return - bh
        v7_alphas.append(a7); v8_alphas.append(a8)
        d = a8 - a7
        w = "v8" if d > 0.001 else ("v7" if d < -0.001 else "=")
        print(f"  {name:<12} {bh:>+6.1%} | {a7:>+9.1%} {a8:>+9.1%} | {d:>+6.1%} | {w}")

    avg7 = statistics.mean(v7_alphas); avg8 = statistics.mean(v8_alphas)
    print(f"\n  Average:              {avg7:>+9.2%} {avg8:>+9.2%} | {avg8-avg7:>+6.2%}")
    v8_wins = sum(1 for a7,a8 in zip(v7_alphas, v8_alphas) if a8 > a7 + 0.001)
    v7_wins = sum(1 for a7,a8 in zip(v7_alphas, v8_alphas) if a7 > a8 + 0.001)
    print(f"  Head-to-head: v7 wins {v7_wins}, v8 wins {v8_wins}")

asyncio.run(main())
