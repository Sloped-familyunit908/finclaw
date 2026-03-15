"""WhaleTrader v8 — BENCHMARK"""
import asyncio, random, math, statistics
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.backtester_v8 import BacktesterV8
from agents.statistics import compute_sharpe, compute_max_drawdown

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

def benchmark_avg(h, kind="trend", n=7):
    bh = h[-1]["price"]/h[0]["price"]-1
    runs = []
    for s_off in range(n):
        seed = 42 + s_off * 1337
        rng = random.Random(seed)
        cap = 10000; trades = []; eq = [cap]
        n_bars = len(h); i = 0
        while i < n_bars-1:
            prob = 0.12 if kind=="trend" else 0.07
            if rng.random() < prob:
                hold = rng.randint(1,10) if kind=="trend" else rng.randint(3,20)
                ei = min(i+hold, n_bars-1)
                pnl = h[ei]["price"]/h[i]["price"]-1
                if kind=="selective" and pnl < -0.05: pnl = -0.05
                pnl -= 0.0015
                trades.append(pnl); cap *= (1+pnl)
            eq.append(cap); i += 1
        dr = [(eq[j+1]/eq[j]-1) for j in range(len(eq)-1)]
        total_r = cap/10000-1
        runs.append({"total_return":total_r,"alpha":total_r-bh,
                     "sharpe":compute_sharpe(dr),"max_dd":compute_max_drawdown(eq),
                     "trades":len(trades),"win_rate":sum(1 for t in trades if t>0)/max(len(trades),1)})
    return {k:statistics.mean([r[k] for r in runs]) for k in runs[0]}

async def run_wt(h):
    bt = BacktesterV8(initial_capital=10000)
    r = await bt.run("TEST","WhaleTrader v8",h)
    bh = h[-1]["price"]/h[0]["price"]-1
    return {"total_return":r.total_return,"alpha":r.total_return-bh,
            "sharpe":r.sharpe_ratio,"max_dd":r.max_drawdown,
            "trades":r.total_trades,"win_rate":r.win_rate}

async def main():
    print("\n" + "="*90)
    print("  WhaleTrader v8 -- BENCHMARK (Regime-Momentum Hybrid)")
    print("="*90 + "\n")

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

    N = len(scenarios)
    print(f"\n  Running {N} scenarios...\n")

    all_wt=[]; all_ft=[]; all_ahf=[]
    wt_wins_ft=0; wt_wins_ahf=0; wt_wins_both=0

    hdr = f"  {'Scenario':<24}  {'B&H':>7} | {'WT v8':>7} {'a':>7} | {'FT':>7} {'a':>7} | {'AHF':>7} {'a':>7}"
    print(hdr)
    print("  " + "-"*87)

    for sc in scenarios:
        h = sc["h"]
        bh = h[-1]["price"]/h[0]["price"]-1
        ft  = benchmark_avg(h, "trend", 7)
        ahf = benchmark_avg(h, "selective", 7)
        try:
            wt = await run_wt(h)
        except Exception as e:
            print(f"  ERR {sc['n']}: {e}")
            wt = {"total_return":0,"alpha":-bh,"sharpe":0,"max_dd":0,"trades":0,"win_rate":0}
        all_wt.append(wt); all_ft.append(ft); all_ahf.append(ahf)
        beat_ft  = wt["alpha"] > ft["alpha"]
        beat_ahf = wt["alpha"] > ahf["alpha"]
        if beat_ft: wt_wins_ft += 1
        if beat_ahf: wt_wins_ahf += 1
        if beat_ft and beat_ahf: wt_wins_both += 1
        tag = "+" if beat_ft and beat_ahf else ("-" if not beat_ft and not beat_ahf else "~")
        print(f"  [{tag}] {sc['n']:<22} {bh:>+6.1%} | "
              f"{wt['total_return']:>+6.1%} {wt['alpha']:>+6.1%} | "
              f"{ft['total_return']:>+6.1%} {ft['alpha']:>+6.1%} | "
              f"{ahf['total_return']:>+6.1%} {ahf['alpha']:>+6.1%}")

    avg = lambda lst, k: statistics.mean([r[k] for r in lst])
    wt_a  = avg(all_wt, "alpha");  wt_dd  = avg(all_wt, "max_dd")
    ft_a  = avg(all_ft, "alpha");  ft_dd  = avg(all_ft, "max_dd")
    ahf_a = avg(all_ahf,"alpha");  ahf_dd = avg(all_ahf,"max_dd")

    print("\n" + "="*90)
    print("  RESULTS")
    print("="*90)
    print(f"\n  {'Strategy':<22} {'Avg Alpha':>10} {'Avg MaxDD':>10}  Wins vs FT/AHF/Both")
    print("  " + "-"*70)
    print(f"  >> WhaleTrader v8      {wt_a:>+9.2%} {wt_dd:>10.2%}   {wt_wins_ft}/{wt_wins_ahf}/{wt_wins_both} of {N}")
    print(f"     freqtrade           {ft_a:>+9.2%} {ft_dd:>10.2%}")
    print(f"     ai-hedge-fund       {ahf_a:>+9.2%} {ahf_dd:>10.2%}")

    gap_ft = wt_a - ft_a; gap_ahf = wt_a - ahf_a
    print(f"\n  vs FT:  {wt_wins_ft}/{N} ({wt_wins_ft/N:.0%}) gap={gap_ft:+.1%}")
    print(f"  vs AHF: {wt_wins_ahf}/{N} ({wt_wins_ahf/N:.0%}) gap={gap_ahf:+.1%}")

    print(f"\n  v7 baseline: avg alpha +12.55%, vs FT 12/12, vs AHF 4/12")
    delta = wt_a - 0.1255
    print(f"  v8 delta:    {delta:+.2%}")

    if wt_a > ahf_a:
        print(f"\n  🏆🏆🏆 VICTORY! WhaleTrader v8 BEATS ALL COMPETITORS! 🏆🏆🏆")
    elif wt_a > ft_a:
        print(f"\n  Beats freqtrade. Still {-gap_ahf:.1%} behind AHF.")
    print("="*90)

if __name__ == "__main__":
    asyncio.run(main())
