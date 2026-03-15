"""Trace ETH trades"""
import asyncio, aiohttp
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.backtester_v7 import BacktesterV7

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
    h = await fetch_crypto("ETH", 365)
    bh = h[-1]["price"]/h[0]["price"]-1
    bt = BacktesterV7(initial_capital=10000)
    r = await bt.run("ETH", "v7", h)
    print(f"ETH: B&H={bh:+.1%}  v7={r.total_return:+.1%}  alpha={r.total_return-bh:+.1%}")
    print(f"AHF=+156.4%  gap={r.total_return-1.564:+.1%}")
    print(f"trades={r.total_trades}  WR={r.win_rate:.0%}  MaxDD={r.max_drawdown:+.1%}")
    print(f"\nTrades:")
    for t in r.trades:
        dur = max((t.exit_time - t.entry_time).days, 1)
        print(f"  {t.signal_source:<12} entry=${t.entry_price:.2f} exit=${t.exit_price:.2f} "
              f"pnl={t.pnl_pct:+.2%} dur={dur}d")

asyncio.run(main())
