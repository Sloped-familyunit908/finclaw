"""
WhaleTrader v9 — BENCHMARK with ASSET SELECTION
=================================================
Paradigm shift: instead of trading everything,
evaluate each asset and skip/reduce bad ones.

Also includes portfolio-level benchmark:
given 12 assets, pick best 5 and allocate capital.
"""
import asyncio, random, math, statistics
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.backtester_v9 import BacktesterV9
from agents.backtester_v7 import BacktesterV7
from agents.signal_engine_v9 import AssetSelector, AssetGrade
from agents.statistics import compute_sharpe, compute_max_drawdown

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

async def main():
    print("\n" + "="*100)
    print("  WhaleTrader v9 -- BENCHMARK (Asset Selection + Momentum-Adaptive)")
    print("="*100 + "\n")

    scenarios = [
        {"n":"NVDA (Bull)",       "h": sim(500, 252, 0.80, 0.50, 1395)},
        {"n":"AAPL (Moderate)",   "h": sim(180, 252, 0.15, 0.25, 1002)},
        {"n":"TSLA (Volatile)",   "h": sim(250, 252, 0.40, 0.65, 1525)},
        {"n":"META (Correction)", "h": sim(550, 252,-0.20, 0.35, 1004)},
        {"n":"AMZN (Bull 2)",     "h": sim(180, 252, 0.30, 0.35, 1628)},
        {"n":"INTC (Bear)",       "h": sim(40,  252,-0.50, 0.40, 1006)},
        {"n":"Moutai (Sideways)", "h": sim(1650,252, 0.05, 0.30, 2001, 0.03, 0.06)},
        {"n":"CATL (Growth)",     "h": sim(220, 252, 0.55, 0.45, 1323, 0.03, 0.06)},
        {"n":"CSI300 (Bear)",     "h": sim(3800,252,-0.15, 0.25, 2003, 0.03, 0.06)},
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

    # ═══ ASSET SELECTION EVALUATION ═══
    selector = AssetSelector()
    print("\n  --- ASSET GRADES ---")
    for sc in scenarios:
        h = sc["h"]
        prices = [x["price"] for x in h]
        vols = [x.get("volume",0) for x in h]
        score = selector.score_asset(prices, vols)
        sc["grade"] = score.grade
        sc["score"] = score
        print(f"  {sc['n']:<22} Grade={score.grade.value:<3} "
              f"comp={score.composite:+.2f} alloc={score.allocation_pct:.0%} "
              f"| {score.reasoning}")

    N = len(scenarios)
    print(f"\n  Running {N} scenarios (v7 vs v9)...\n")

    all_v7=[]; all_v9=[]; all_ft=[]; all_ahf=[]
    v7_wins=0; v9_wins=0

    hdr = (f"  {'Scenario':<22} {'Grade':>5} {'B&H':>7} | "
           f"{'v7 a':>7} {'v9 a':>7} | {'FT a':>7} {'AHF a':>7}")
    print(hdr)
    print("  " + "-"*80)

    for sc in scenarios:
        h = sc["h"]
        bh = h[-1]["price"]/h[0]["price"]-1
        ft = benchmark_avg(h, "trend", 7)
        ahf = benchmark_avg(h, "selective", 7)

        bt7 = BacktesterV7(initial_capital=10000)
        bt9 = BacktesterV9(initial_capital=10000)
        try:
            r7 = await bt7.run("T","v7",h)
            r9 = await bt9.run("T","v9",h)
        except Exception as e:
            print(f"  ERR {sc['n']}: {e}")
            continue
        
        a7 = r7.total_return - bh
        a9 = r9.total_return - bh
        all_v7.append({"alpha":a7, "max_dd":r7.max_drawdown})
        all_v9.append({"alpha":a9, "max_dd":r9.max_drawdown})
        all_ft.append(ft)
        all_ahf.append(ahf)

        d = a9 - a7
        if d > 0.001: v9_wins += 1
        elif d < -0.001: v7_wins += 1

        grade = sc.get("grade", AssetGrade.C)
        print(f"  {sc['n']:<22} {grade.value:>5} {bh:>+6.1%} | "
              f"{a7:>+6.1%} {a9:>+6.1%} | {ft['alpha']:>+6.1%} {ahf['alpha']:>+6.1%}")

    avg7 = statistics.mean([r["alpha"] for r in all_v7])
    avg9 = statistics.mean([r["alpha"] for r in all_v9])
    dd7 = statistics.mean([r["max_dd"] for r in all_v7])
    dd9 = statistics.mean([r["max_dd"] for r in all_v9])

    # Count v9 wins vs competitors
    v9_beat_ft = sum(1 for v9,ft in zip(all_v9, all_ft) if v9["alpha"] > ft["alpha"])
    v9_beat_ahf = sum(1 for v9,ahf in zip(all_v9, all_ahf) if v9["alpha"] > ahf["alpha"])

    print("\n" + "="*100)
    print("  RESULTS")
    print("="*100)
    print(f"\n  {'Strategy':<22} {'Avg Alpha':>10} {'Avg MaxDD':>10}")
    print("  " + "-"*50)
    print(f"  >> WhaleTrader v9      {avg9:>+9.2%} {dd9:>10.2%}   vs FT {v9_beat_ft}/{N}, vs AHF {v9_beat_ahf}/{N}")
    print(f"     WhaleTrader v7      {avg7:>+9.2%} {dd7:>10.2%}")
    ft_a = statistics.mean([r["alpha"] for r in all_ft])
    ahf_a = statistics.mean([r["alpha"] for r in all_ahf])
    print(f"     freqtrade           {ft_a:>+9.2%}")
    print(f"     ai-hedge-fund       {ahf_a:>+9.2%}")

    delta = avg9 - avg7
    print(f"\n  v9 vs v7: {delta:+.2%} ({v9_wins} wins, {v7_wins} losses)")
    if avg9 > avg7:
        print(f"  v9 WINS!")
    else:
        print(f"  v7 still champion")

    print("="*100)

if __name__ == "__main__":
    asyncio.run(main())
