"""Analyze AHF simulation fairness on crypto data."""
import random, math, statistics
from datetime import datetime, timedelta
import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.statistics import compute_sharpe, compute_max_drawdown

async def fetch_crypto(asset, days=365):
    import aiohttp
    coin = {"BTC":"bitcoin","ETH":"ethereum","SOL":"solana"}[asset]
    url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart"
    async with aiohttp.ClientSession() as s:
        async with s.get(url, params={"vs_currency":"usd","days":str(days)}) as r:
            data = await r.json()
    return [{"date":datetime.fromtimestamp(ts/1000),"price":p} for ts,p in data.get("prices",[])]

def run_ahf_detail(h, seed):
    """Run a single AHF simulation and show all trades."""
    bh = h[-1]["price"]/h[0]["price"]-1
    rng = random.Random(seed)
    cap = 10000; trades = []; n_bars = len(h); i = 0
    while i < n_bars-1:
        if rng.random() < 0.07:
            hold = rng.randint(3,20)
            ei = min(i+hold, n_bars-1)
            pnl = h[ei]["price"]/h[i]["price"]-1
            raw_pnl = pnl
            if pnl < -0.05: pnl = -0.05  # Perfect stop
            pnl -= 0.0015
            cap *= (1+pnl)
            trades.append({"bar_in":i,"bar_out":ei,"raw_pnl":raw_pnl,"capped_pnl":pnl,"cap_after":cap})
        i += 1
    total_r = cap/10000-1
    return total_r, total_r - bh, trades

async def main():
    for asset in ["ETH","SOL","BTC"]:
        h = await fetch_crypto(asset, 365)
        bh = h[-1]["price"]/h[0]["price"]-1
        print(f"\n{'='*60}")
        print(f"{asset}: B&H = {bh:+.1%}, {len(h)} bars")
        print(f"Price: ${h[0]['price']:,.0f} -> ${h[-1]['price']:,.0f}")
        
        # Show price volatility
        daily_rets = [h[i]["price"]/h[i-1]["price"]-1 for i in range(1, len(h))]
        vol = statistics.stdev(daily_rets) * math.sqrt(365)
        print(f"Annualized vol: {vol:.0%}")
        
        # Run 7 seeds
        alphas = []
        for s_off in range(7):
            seed = 42 + s_off * 1337
            ret, alpha, trades = run_ahf_detail(h, seed)
            alphas.append(alpha)
            # Count how many trades had loss capped
            capped = sum(1 for t in trades if t["raw_pnl"] < -0.05)
            profitable = sum(1 for t in trades if t["capped_pnl"] > 0)
            print(f"  Seed {seed:5d}: ret={ret:+6.1%} alpha={alpha:+6.1%} "
                  f"trades={len(trades)} capped={capped} wins={profitable} "
                  f"WR={profitable/max(len(trades),1):.0%}")
        
        avg_alpha = statistics.mean(alphas)
        print(f"  AVG ALPHA: {avg_alpha:+.1%}")
        print(f"  ISSUE: {'UNFAIR - random sim produces massive alpha on volatile crypto!' if abs(avg_alpha) > 30 else 'Reasonable'}")
        await asyncio.sleep(5)

asyncio.run(main())
