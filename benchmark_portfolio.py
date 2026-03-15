"""
WhaleTrader Portfolio Benchmark — STOCK SELECTION TEST
=======================================================
The REAL test of stock selection: given a basket of 12 assets,
allocate capital to the best ones. Compare:
1. Equal-weight (1/12 each) — naive
2. WhaleTrader stock selection (grade-weighted)
3. Oracle (hindsight-optimal, upper bound)
"""
import asyncio, random, math, statistics
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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

async def run_wt(h):
    bt = BacktesterV7(initial_capital=10000)
    r = await bt.run("T","v7",h)
    bh = h[-1]["price"]/h[0]["price"]-1
    return {"total_return":r.total_return,"alpha":r.total_return-bh,
            "sharpe":r.sharpe_ratio,"max_dd":r.max_drawdown}

async def main():
    print("\n" + "="*100)
    print("  WhaleTrader — PORTFOLIO STOCK SELECTION TEST")
    print("="*100 + "\n")

    scenarios = [
        {"n":"NVDA",    "h": sim(500, 252, 0.80, 0.50, 1395)},
        {"n":"AAPL",    "h": sim(180, 252, 0.15, 0.25, 1002)},
        {"n":"TSLA",    "h": sim(250, 252, 0.40, 0.65, 1525)},
        {"n":"META",    "h": sim(550, 252,-0.20, 0.35, 1004)},
        {"n":"AMZN",    "h": sim(180, 252, 0.30, 0.35, 1628)},
        {"n":"INTC",    "h": sim(40,  252,-0.50, 0.40, 1006)},
        {"n":"Moutai",  "h": sim(1650,252, 0.05, 0.30, 2001, 0.03, 0.06)},
        {"n":"CATL",    "h": sim(220, 252, 0.55, 0.45, 1323, 0.03, 0.06)},
        {"n":"CSI300",  "h": sim(3800,252,-0.15, 0.25, 2003, 0.03, 0.06)},
    ]

    print("  Fetching crypto...")
    for asset in ["BTC","ETH","SOL"]:
        try:
            h = await fetch_crypto(asset, 365)
            if h and len(h) > 30:
                bh = (h[-1]["price"]/h[0]["price"]-1)*100
                print(f"    {asset}: ${h[0]['price']:,.0f} -> ${h[-1]['price']:,.0f} ({bh:+.1f}%)")
                scenarios.append({"n":asset,"h":h})
            await asyncio.sleep(5)
        except Exception as e:
            print(f"    {asset}: SKIP ({e})")

    N = len(scenarios)

    # ═══ Step 1: Evaluate all assets at day 60 (after enough data) ═══
    selector = AssetSelector()
    print(f"\n  --- ASSET EVALUATION (using first 60 bars as lookback) ---")
    grades = []
    for sc in scenarios:
        h = sc["h"]
        prices = [x["price"] for x in h[:120]]  # use first 120 bars for evaluation
        vols = [x.get("volume",0) for x in h[:120]]
        score = selector.score_asset(prices, vols)
        sc["grade"] = score.grade
        sc["composite"] = score.composite
        sc["alloc"] = score.allocation_pct
        grades.append((sc["n"], score))
        print(f"  {sc['n']:<10} Grade={score.grade.value:<3} "
              f"comp={score.composite:+.2f} alloc={score.allocation_pct:.0%} "
              f"| {score.reasoning}")

    # ═══ Step 2: Run WhaleTrader on all assets ═══
    print(f"\n  --- INDIVIDUAL PERFORMANCE ---")
    results = {}
    for sc in scenarios:
        try:
            r = await run_wt(sc["h"])
        except:
            r = {"total_return":0,"alpha":0,"sharpe":0,"max_dd":0}
        results[sc["n"]] = r
        bh = sc["h"][-1]["price"]/sc["h"][0]["price"]-1
        print(f"  {sc['n']:<10} B&H={bh:>+6.1%} | v7_ret={r['total_return']:>+6.1%} alpha={r['alpha']:>+6.1%}")

    # ═══ Step 3: Portfolio construction strategies ═══
    portfolio_capital = 100000

    # Strategy 1: Equal-weight (all assets)
    ew_alloc = {sc["n"]: 1.0/N for sc in scenarios}
    ew_return = sum(results[name]["total_return"] * weight
                    for name, weight in ew_alloc.items())

    # Strategy 2: Grade-weighted (WhaleTrader selection)
    total_alloc = sum(sc["alloc"] for sc in scenarios if sc["alloc"] > 0)
    if total_alloc > 0:
        wt_alloc = {sc["n"]: sc["alloc"]/total_alloc for sc in scenarios if sc["alloc"] > 0}
    else:
        wt_alloc = ew_alloc
    wt_return = sum(results[name]["total_return"] * weight
                    for name, weight in wt_alloc.items())

    # Strategy 3: Top-3 concentration (highest grade only)
    ranked = sorted(scenarios, key=lambda x: x.get("composite", 0), reverse=True)
    top3 = ranked[:3]
    t3_alloc = {sc["n"]: 1.0/3 for sc in top3}
    t3_return = sum(results[name]["total_return"] * weight
                    for name, weight in t3_alloc.items())

    # Strategy 4: Avoid F-grade (equal weight among non-F)
    non_f = [sc for sc in scenarios if sc.get("grade") != AssetGrade.F]
    if non_f:
        nf_alloc = {sc["n"]: 1.0/len(non_f) for sc in non_f}
    else:
        nf_alloc = ew_alloc
    nf_return = sum(results[name]["total_return"] * weight
                    for name, weight in nf_alloc.items())

    # Strategy 5: Oracle (hindsight, top 3 by actual return)
    sorted_by_actual = sorted(scenarios, key=lambda sc: results[sc["n"]]["total_return"], reverse=True)
    oracle_top3 = sorted_by_actual[:3]
    oracle_return = sum(results[sc["n"]]["total_return"] / 3 for sc in oracle_top3)

    # Strategy 6: B&H equal weight
    bh_returns = {sc["n"]: sc["h"][-1]["price"]/sc["h"][0]["price"]-1 for sc in scenarios}
    bh_ew_return = sum(r/N for r in bh_returns.values())

    print(f"\n" + "="*100)
    print(f"  PORTFOLIO RESULTS (capital = ${portfolio_capital:,})")
    print(f"="*100)
    print(f"\n  {'Strategy':<35} {'Return':>10} {'$ P&L':>12}  Assets")
    print(f"  " + "-"*80)
    print(f"  B&H Equal Weight                  {bh_ew_return:>+9.1%} {portfolio_capital*bh_ew_return:>+11,.0f}  all {N}")
    print(f"  Equal Weight (WT v7)              {ew_return:>+9.1%} {portfolio_capital*ew_return:>+11,.0f}  all {N}")
    print(f"  Avoid F-grade (WT v7)             {nf_return:>+9.1%} {portfolio_capital*nf_return:>+11,.0f}  {len(non_f)} assets")
    print(f"  >> Grade-Weighted (WT v9 select)  {wt_return:>+9.1%} {portfolio_capital*wt_return:>+11,.0f}  {len(wt_alloc)} assets")
    print(f"  Top-3 Concentration               {t3_return:>+9.1%} {portfolio_capital*t3_return:>+11,.0f}  {', '.join(sc['n'] for sc in top3)}")
    print(f"  Oracle (hindsight top 3)          {oracle_return:>+9.1%} {portfolio_capital*oracle_return:>+11,.0f}  {', '.join(sc['n'] for sc in oracle_top3)}")

    # Show allocation detail for grade-weighted
    print(f"\n  Grade-Weighted Allocation:")
    for name, w in sorted(wt_alloc.items(), key=lambda x: -x[1]):
        grade = next((sc.get("grade",AssetGrade.C).value for sc in scenarios if sc["n"]==name), "?")
        print(f"    {name:<10} {grade:>3}  {w:>5.0%}  ${portfolio_capital*w:>8,.0f}")

    print(f"\n  Top-3 Concentration:")
    for sc in top3:
        print(f"    {sc['n']:<10} {sc.get('grade',AssetGrade.C).value:>3}  33%  ${portfolio_capital/3:>8,.0f}")

    # ═══ Alpha comparison ═══
    ew_alpha = ew_return - bh_ew_return
    nf_alpha = nf_return - bh_ew_return
    wt_alpha = wt_return - bh_ew_return
    t3_alpha = t3_return - bh_ew_return

    print(f"\n  --- ALPHA vs B&H Equal Weight ---")
    print(f"  Equal Weight v7:      {ew_alpha:>+.2%}")
    print(f"  Avoid F-grade:        {nf_alpha:>+.2%}")
    print(f"  Grade-Weighted:       {wt_alpha:>+.2%}")
    print(f"  Top-3 Concentration:  {t3_alpha:>+.2%}")

    print("="*100)

if __name__ == "__main__":
    asyncio.run(main())
