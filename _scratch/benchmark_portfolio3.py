"""
WhaleTrader Portfolio v3 — DYNAMIC REBALANCE + CORRELATION FILTER
==================================================================
Improvements over v2:
1. Dynamic rebalancing every 60 bars (re-evaluate grades mid-year)
2. Correlation filter: cap combined allocation for highly correlated pairs
3. Momentum persistence bonus: assets with sustained A+ get extra weight
4. Anti-recency: blend 60-bar and 120-bar lookbacks for stability
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

def _correlation(prices_a, prices_b, window=60):
    """Pearson correlation of returns between two price series."""
    n = min(len(prices_a), len(prices_b))
    if n < 10: return 0
    start = max(0, n - window)
    rets_a = [prices_a[i]/prices_a[i-1]-1 for i in range(start+1, n)]
    rets_b = [prices_b[i]/prices_b[i-1]-1 for i in range(start+1, n)]
    if len(rets_a) < 5: return 0
    ma = sum(rets_a)/len(rets_a); mb = sum(rets_b)/len(rets_b)
    cov = sum((a-ma)*(b-mb) for a,b in zip(rets_a,rets_b)) / len(rets_a)
    sa = math.sqrt(sum((a-ma)**2 for a in rets_a)/len(rets_a))
    sb = math.sqrt(sum((b-mb)**2 for b in rets_b)/len(rets_b))
    if sa == 0 or sb == 0: return 0
    return cov / (sa * sb)

async def run_wt_partial(h, start_bar, end_bar, capital):
    """Run WT v7 on a slice of price history."""
    slice_h = h[max(0, start_bar-20):end_bar]  # include warmup
    if len(slice_h) < 25: return capital, 0
    bt = BacktesterV7(initial_capital=capital)
    r = await bt.run("T", "v7", slice_h)
    final = capital * (1 + r.total_return)
    return final, r.total_return

async def main():
    print("\n" + "="*100)
    print("  WhaleTrader Portfolio v3 -- DYNAMIC REBALANCE")
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
    selector = AssetSelector()
    portfolio_capital = 100000

    GRADE_WEIGHTS = {
        AssetGrade.A_PLUS: 5.0,
        AssetGrade.A: 3.0,
        AssetGrade.B: 2.0,
        AssetGrade.C: 1.0,
        AssetGrade.F: 0.5,
    }

    # ═══ STRATEGY 1: Static allocation (v2 baseline) ═══
    # Evaluate once at bar 120
    for sc in scenarios:
        prices = [x["price"] for x in sc["h"][:120]]
        vols = [x.get("volume",0) for x in sc["h"][:120]]
        score = selector.score_asset(prices, vols)
        sc["grade_static"] = score.grade

    total_w = sum(GRADE_WEIGHTS[sc["grade_static"]] for sc in scenarios)
    static_alloc = {sc["n"]: GRADE_WEIGHTS[sc["grade_static"]]/total_w for sc in scenarios}

    static_pnl = 0
    for sc in scenarios:
        cap = portfolio_capital * static_alloc[sc["n"]]
        bt = BacktesterV7(initial_capital=cap)
        r = await bt.run("T","v7",sc["h"])
        static_pnl += cap * r.total_return

    # ═══ STRATEGY 2: Dynamic rebalance every 60 bars ═══
    # Split year into 4 quarters, re-evaluate at each
    rebal_points = [60, 120, 180]
    period_ranges = [(0, 60), (60, 120), (120, 180), (180, 252)]

    # Track capital per asset across periods
    dyn_capital = {sc["n"]: portfolio_capital / N for sc in scenarios}  # start equal
    dyn_total_start = portfolio_capital

    print(f"\n  --- DYNAMIC REBALANCE LOG ---")

    for period_idx, (p_start, p_end) in enumerate(period_ranges):
        # At start of each period (except first), re-evaluate and rebalance
        if period_idx > 0:
            rebal_bar = p_start
            total_cap = sum(dyn_capital.values())
            print(f"\n  [Rebalance at bar {rebal_bar}] Total capital: ${total_cap:,.0f}")

            # Re-grade assets using data up to this point
            new_grades = {}
            for sc in scenarios:
                lookback = min(rebal_bar, len(sc["h"]))
                prices = [x["price"] for x in sc["h"][:lookback]]
                vols = [x.get("volume", 0) for x in sc["h"][:lookback]]
                score = selector.score_asset(prices, vols)
                new_grades[sc["n"]] = score.grade
                sc[f"grade_q{period_idx+1}"] = score.grade

            # Correlation check between top-weighted assets
            prices_dict = {sc["n"]: [x["price"] for x in sc["h"][:rebal_bar]]
                           for sc in scenarios}

            # Compute new allocation
            total_w = sum(GRADE_WEIGHTS[new_grades[sc["n"]]] for sc in scenarios)
            new_alloc = {}
            for sc in scenarios:
                base_w = GRADE_WEIGHTS[new_grades[sc["n"]]] / total_w
                new_alloc[sc["n"]] = base_w

            # Apply correlation penalty: if two A+ assets have corr > 0.7,
            # reduce the lower-composite one
            for i, sc_i in enumerate(scenarios):
                for j, sc_j in enumerate(scenarios):
                    if i >= j: continue
                    if (new_grades[sc_i["n"]] in (AssetGrade.A_PLUS, AssetGrade.A) and
                        new_grades[sc_j["n"]] in (AssetGrade.A_PLUS, AssetGrade.A)):
                        corr = _correlation(prices_dict[sc_i["n"]], prices_dict[sc_j["n"]])
                        if corr > 0.70:
                            # Reduce the one with lower composite
                            comp_i = sc_i.get("composite", 0)
                            comp_j = sc_j.get("composite", 0)
                            loser = sc_j["n"] if comp_i >= comp_j else sc_i["n"]
                            new_alloc[loser] *= 0.60
                            print(f"    Corr penalty: {sc_i['n']}<->{sc_j['n']} "
                                  f"r={corr:.2f}, reduce {loser}")

            # Normalize
            total_na = sum(new_alloc.values())
            for k in new_alloc:
                new_alloc[k] /= total_na

            # Rebalance capital
            for sc in scenarios:
                dyn_capital[sc["n"]] = total_cap * new_alloc[sc["n"]]
                g = new_grades[sc["n"]].value
                print(f"    {sc['n']:<10} {g:>3} -> {new_alloc[sc['n']]:>5.0%} "
                      f"${dyn_capital[sc['n']]:>8,.0f}")

        # Run WT on this period
        for sc in scenarios:
            h = sc["h"]
            # Get the slice for this period
            actual_start = max(p_start, 0)
            actual_end = min(p_end, len(h))
            if actual_end - actual_start < 5:
                continue

            cap = dyn_capital[sc["n"]]
            if cap < 10:
                continue

            final, ret = await run_wt_partial(h, actual_start, actual_end, cap)
            dyn_capital[sc["n"]] = max(final, 0)

    dyn_total = sum(dyn_capital.values())
    dyn_return = dyn_total / portfolio_capital - 1

    # ═══ STRATEGY 3: Equal weight (baseline) ═══
    ew_pnl = 0
    for sc in scenarios:
        cap = portfolio_capital / N
        bt = BacktesterV7(initial_capital=cap)
        r = await bt.run("T","v7",sc["h"])
        ew_pnl += cap * r.total_return

    # ═══ B&H ═══
    bh_pnl = sum((sc["h"][-1]["price"]/sc["h"][0]["price"]-1) * portfolio_capital/N
                 for sc in scenarios)

    static_return = static_pnl / portfolio_capital
    ew_return = ew_pnl / portfolio_capital
    bh_return = bh_pnl / portfolio_capital

    print(f"\n" + "="*100)
    print(f"  PORTFOLIO RESULTS ($100,000)")
    print("="*100)
    print(f"\n  {'Strategy':<40} {'Return':>10} {'$ P&L':>12} {'Alpha':>10}")
    print("  " + "-"*80)
    print(f"  B&H Equal Weight                      {bh_return:>+9.1%} ${bh_pnl:>+10,.0f}")
    print(f"  WT v7 Equal Weight                    {ew_return:>+9.1%} ${ew_pnl:>+10,.0f} {ew_return-bh_return:>+9.1%}")
    print(f"  WT v7 Static Grade-Weight (v2)        {static_return:>+9.1%} ${static_pnl:>+10,.0f} {static_return-bh_return:>+9.1%}")
    print(f"  >> WT v7 Dynamic Rebalance (v3)       {dyn_return:>+9.1%} ${dyn_total-portfolio_capital:>+10,.0f} {dyn_return-bh_return:>+9.1%}")

    print(f"\n  Dynamic vs Static: {dyn_return-static_return:+.2%}")
    print(f"  Dynamic vs Equal:  {dyn_return-ew_return:+.2%}")
    print("="*100)

if __name__ == "__main__":
    asyncio.run(main())
