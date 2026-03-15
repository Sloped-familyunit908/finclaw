"""Diagnose ETH + Moutai v6 vs v7"""
import asyncio, aiohttp, random, math
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.backtester_v5 import BacktesterV5
from agents.backtester_v7 import BacktesterV7

def sim(start, days, ret, vol, seed=42, jp=0.02, js=0.04):
    rng = random.Random(seed)
    dt = 1/252; prices = [start]
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
    print("Fetching ETH...")
    eth = await fetch_crypto("ETH", 365)
    bh = eth[-1]["price"] / eth[0]["price"] - 1
    print(f"ETH B&H: {bh:+.1%}")

    mt = sim(1650, 252, 0.05, 0.30, 2001, 0.03, 0.06)
    bh_mt = mt[-1]["price"] / mt[0]["price"] - 1

    for name, h, bh_val in [("ETH", eth, bh), ("Moutai", mt, bh_mt)]:
        print(f"\n{'='*70}")
        print(f"  {name}  B&H: {bh_val:+.1%}")
        print(f"{'='*70}")
        for label, BT in [("v6", BacktesterV5), ("v7", BacktesterV7)]:
            bt = BT(initial_capital=10000)
            r = await bt.run("TEST", label, h)
            alpha = r.total_return - bh_val
            print(f"\n  {label}: ret={r.total_return:+.1%} alpha={alpha:+.1%} "
                  f"MaxDD={r.max_drawdown:.1%} trades={r.total_trades} WR={r.win_rate:.0%}")
            for t in r.trades:
                dur = (t.exit_time - t.entry_time).days
                print(f"    {t.signal_source:<12} entry=${t.entry_price:.2f} exit=${t.exit_price:.2f} "
                      f"pnl={t.pnl_pct:+.1%} dur={dur}d")

asyncio.run(main())
