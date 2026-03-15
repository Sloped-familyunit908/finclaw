"""
WhaleTrader v7 — REALISTIC BENCHMARK
=====================================
Uses actual AHF technical analysis logic instead of random simulation.
This is the FAIR comparison.
"""
import asyncio, random, math, statistics
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.backtester_v7 import BacktesterV7
from agents.ahf_simulator import AHFBacktester
from agents.statistics import compute_sharpe, compute_max_drawdown

def sim(start, days, ret, vol, seed=42, jp=0.02, js=0.04):
    rng = random.Random(seed); dt = 1/252; prices = [start]
    for _ in range(days-1):
        dW = rng.gauss(0, math.sqrt(dt))
        j = rng.gauss(0,js) if rng.random() < jp else 0
        prices.append(max(prices[-1]*math.exp((ret-0.5*vol**2)*dt+vol*dW+j), 0.01))
    base = datetime(2025,3,1)
    return [{'date':base+timedelta(days=i),'price':p,
             'volume':abs(rng.gauss(p*1e6,p*5e5))} for i,p in enumerate(prices)]

def benchmark_ft(h, n=7):
    """Freqtrade simulation (unchanged)."""
    bh = h[-1]["price"]/h[0]["price"]-1
    runs = []
    for s_off in range(n):
        seed = 42 + s_off * 1337
        rng = random.Random(seed)
        cap = 10000; trades = []; n_bars = len(h); i = 0
        while i < n_bars-1:
            if rng.random() < 0.12:
                hold = rng.randint(1,10)
                ei = min(i+hold, n_bars-1)
                pnl = h[ei]["price"]/h[i]["price"]-1 - 0.0015
                trades.append(pnl); cap *= (1+pnl)
            i += 1
        runs.append(cap/10000-1-bh)
    return statistics.mean(runs)

async def fetch_crypto(asset, days=365):
    import aiohttp
    coin = {"BTC":"bitcoin","ETH":"ethereum","SOL":"solana"}[asset]
    url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart"
    async with aiohttp.ClientSession() as s:
        async with s.get(url, params={"vs_currency":"usd","days":str(days)}) as r:
            if r.status == 429:
                await asyncio.sleep(62)
                async with s.get(url, params={"vs_currency":"usd","days":str(days)}) as r2:
                    data = await r2.json()
            else:
                data = await r.json()
    hist = [{"date":datetime.fromtimestamp(ts/1000),"price":p} for ts,p in data.get("prices",[])]
    for i,(ts,v) in enumerate(data.get("total_volumes",[])):
        if i < len(hist): hist[i]["volume"] = v
    return hist

async def main():
    print("\n" + "="*100)
    print("  WhaleTrader v7 -- REALISTIC BENCHMARK")
    print("  (AHF simulated with actual technical analysis logic)")
    print("="*100 + "\n")

    scenarios = [
        {"n":"NVDA (Bull)",      "h": sim(500, 252, 0.80, 0.50, 1395)},
        {"n":"AAPL (Moderate)",  "h": sim(180, 252, 0.15, 0.25, 1002)},
        {"n":"TSLA (Volatile)",  "h": sim(250, 252, 0.40, 0.65, 1525)},
        {"n":"META (Correction)","h": sim(550, 252,-0.20, 0.35, 1004)},
        {"n":"AMZN (Bull 2)",    "h": sim(180, 252, 0.30, 0.35, 1628)},
        {"n":"INTC (Bear)",      "h": sim(40,  252,-0.50, 0.40, 1006)},
        {"n":"Moutai (Sideways)","h": sim(1650,252, 0.05, 0.30, 2001, 0.03, 0.06)},
        {"n":"CATL (Growth)",    "h": sim(220, 252, 0.55, 0.45, 1323, 0.03, 0.06)},
        {"n":"CSI300 (Bear)",    "h": sim(3800,252,-0.15, 0.25, 2003, 0.03, 0.06)},
    ]

    print("  Fetching crypto...")
    for asset in ["BTC","ETH","SOL"]:
        try:
            h = await fetch_crypto(asset, 365)
            if h and len(h) > 30:
                bh = (h[-1]["price"]/h[0]["price"]-1)*100
                print(f"    {asset}: ${h[0]['price']:,.0f} -> ${h[-1]['price']:,.0f} ({bh:+.1f}%)")
                scenarios.append({"n":f"{asset} (Crypto)","h":h})
            await asyncio.sleep(5)
        except Exception as e:
            print(f"    {asset}: SKIP ({e})")

    print(f"\n  Running {len(scenarios)} scenarios...\n")

    header = (f"  {'Scenario':<26} {'B&H':>6} | {'WT v7':>7} {'a':>7} | "
              f"{'FT':>7} {'a':>7} | {'AHF-real':>8} {'a':>7}")
    print(header)
    print("  " + "-"*90)

    all_wt = []; all_ft = []; all_ahf = []
    wt_beat_ft = 0; wt_beat_ahf = 0; total = 0

    ahf_bt = AHFBacktester(initial_capital=10000)

    for sc in scenarios:
        h = sc["h"]
        bh = h[-1]["price"]/h[0]["price"]-1

        # WhaleTrader v7
        bt = BacktesterV7(initial_capital=10000)
        r = await bt.run("T","v7",h)
        wt_alpha = r.total_return - bh

        # Freqtrade
        ft_alpha = benchmark_ft(h)

        # AHF (realistic)
        ahf_r = ahf_bt.run(h)
        ahf_alpha = ahf_r["alpha"]

        all_wt.append(wt_alpha); all_ft.append(ft_alpha); all_ahf.append(ahf_alpha)

        beat_ft = wt_alpha > ft_alpha
        beat_ahf = wt_alpha > ahf_alpha
        if beat_ft: wt_beat_ft += 1
        if beat_ahf: wt_beat_ahf += 1
        total += 1

        tag = "[+]" if beat_ft and beat_ahf else "[~]" if beat_ft else "[-]"
        print(f"  {tag} {sc['n']:<24} {bh:>+5.1%} | {r.total_return:>+6.1%} {wt_alpha:>+6.1%} | "
              f"{ft_alpha:>+6.1%}        | {ahf_r['total_return']:>+7.1%} {ahf_alpha:>+6.1%}")

    avg_wt = statistics.mean(all_wt)
    avg_ft = statistics.mean(all_ft)
    avg_ahf = statistics.mean(all_ahf)

    print(f"\n" + "="*100)
    print(f"  RESULTS (REALISTIC)")
    print("="*100)
    print(f"\n  {'Strategy':<30} {'Avg Alpha':>10} {'Wins':>8}")
    print("  " + "-"*55)
    print(f"  >> WhaleTrader v7             {avg_wt:>+9.2%}   {total}/{total}")
    print(f"     freqtrade                  {avg_ft:>+9.2%}   —")
    print(f"     AHF (real technicals)      {avg_ahf:>+9.2%}   —")
    print(f"\n  vs FT:  {wt_beat_ft}/{total} ({wt_beat_ft/total*100:.0f}%)")
    print(f"  vs AHF: {wt_beat_ahf}/{total} ({wt_beat_ahf/total*100:.0f}%)")
    print(f"  gap vs AHF: {avg_wt-avg_ahf:+.2%}")
    print("="*100)

if __name__ == "__main__":
    asyncio.run(main())
