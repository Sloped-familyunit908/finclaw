"""Debug ETH v7 trade details — regime tracking"""
import asyncio, aiohttp
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.signal_engine_v7 import SignalEngineV7, MarketRegime

async def fetch_crypto(asset, days=365):
    coin = {"ETH":"ethereum"}[asset]
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
    prices = [b["price"] for b in h]
    volumes = [b.get("volume",0) for b in h]

    engine = SignalEngineV7()
    # Find where entry around $1794 happens
    for i in range(20, len(prices)):
        if abs(prices[i] - 1794.87) < 5:
            sig = engine.generate_signal(prices[:i+1], volumes[:i+1], 0)
            print(f"  i={i} price=${prices[i]:.2f} regime={sig.regime.value} "
                  f"signal={sig.signal} conf={sig.confidence:.2f} "
                  f"trailing={sig.trailing_stop_pct:.2%} stop={sig.stop_loss:.2f}")

    # Check regime at peak ($3295 area)
    print("\n--- Around peak ---")
    engine2 = SignalEngineV7()
    for i in range(20, len(prices)):
        sig = engine2.generate_signal(prices[:i+1], volumes[:i+1], 1.0)
        if prices[i] > 3200 or (i > 250 and prices[i] > 2800):
            print(f"  i={i} price=${prices[i]:.2f} regime={sig.regime.value} "
                  f"signal={sig.signal} trailing={sig.trailing_stop_pct:.2%}")
        if i > 280 and prices[i] < 2900:
            break

asyncio.run(main())
