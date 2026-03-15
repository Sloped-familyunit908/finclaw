"""Debug SOL v7 vs v8"""
import asyncio, aiohttp
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.backtester_v7 import BacktesterV7
from agents.backtester_v8 import BacktesterV8

async def fetch_crypto(asset, days=365):
    coin = {"SOL":"solana"}[asset]
    url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart"
    async with aiohttp.ClientSession() as s:
        async with s.get(url, params={"vs_currency":"usd","days":str(days)}) as r:
            data = await r.json()
    hist = [{"date":datetime.fromtimestamp(ts/1000),"price":p} for ts,p in data.get("prices",[])]
    for i,(ts,v) in enumerate(data.get("total_volumes",[])):
        if i < len(hist): hist[i]["volume"] = v
    return hist

async def main():
    h = await fetch_crypto("SOL", 365)
    bh = h[-1]["price"] / h[0]["price"] - 1
    print(f"SOL B&H: {bh:+.1%}\n")
    for label, BT in [("v7", BacktesterV7), ("v8", BacktesterV8)]:
        bt = BT(initial_capital=10000)
        r = await bt.run("SOL", label, h)
        alpha = r.total_return - bh
        print(f"  {label}: ret={r.total_return:+.1%} alpha={alpha:+.1%} trades={r.total_trades} WR={r.win_rate:.0%}")
        for t in r.trades:
            dur = (t.exit_time - t.entry_time).days
            print(f"    {t.signal_source:<12} entry=${t.entry_price:.2f} exit=${t.exit_price:.2f} "
                  f"pnl={t.pnl_pct:+.1%} dur={dur}d")

asyncio.run(main())
