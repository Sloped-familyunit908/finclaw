"""
WhaleTrader Portfolio v3b — DYNAMIC REBALANCE (Fixed)
=====================================================
Fix: don't slice price history! Run full backtest per asset,
then weight by time-varying grade allocation.

Approach: evaluate grades at bar 0/60/120/180.
Weight the P&L of each quarter by the grade at that time.
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

async def main():
    print("\n" + "="*100)
    print("  WhaleTrader Portfolio v3b -- DYNAMIC REBALANCE (Fixed)")
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

    # ═══ Run full backtest on each asset (get equity curves) ═══
    print(f"\n  Running full backtests...")
    asset_results = {}
    for sc in scenarios:
        bt = BacktesterV7(initial_capital=10000)
        r = await bt.run("T","v7",sc["h"])
        asset_results[sc["n"]] = {
            "total_return": r.total_return,
            "equity_curve": r.equity_curve,
            "bh": sc["h"][-1]["price"]/sc["h"][0]["price"]-1,
        }
        bh = asset_results[sc["n"]]["bh"]
        print(f"    {sc['n']:<10} B&H={bh:>+6.1%} v7={r.total_return:>+6.1%} alpha={r.total_return-bh:>+6.1%}")

    # ═══ Compute quarterly returns from equity curves ═══
    quarters = [(0, 60), (60, 120), (120, 180), (180, None)]

    print(f"\n  --- QUARTERLY GRADE EVOLUTION ---")

    # For each quarter, determine grades and compute weighted portfolio return
    quarterly_allocs = []

    for q_idx, (q_start, q_end) in enumerate(quarters):
        # Grade at start of quarter
        lookback_bar = max(q_start, 60)
        grades = {}
        composites = {}
        for sc in scenarios:
            h = sc["h"]
            lb = min(lookback_bar, len(h))
            prices = [x["price"] for x in h[:lb]]
            vols = [x.get("volume",0) for x in h[:lb]]
            if len(prices) < 60:
                grades[sc["n"]] = AssetGrade.C
                composites[sc["n"]] = 0
            else:
                score = selector.score_asset(prices, vols)
                grades[sc["n"]] = score.grade
                composites[sc["n"]] = score.composite

        # Compute allocation with correlation penalty
        total_w = sum(GRADE_WEIGHTS[grades[sc["n"]]] for sc in scenarios)
        alloc = {sc["n"]: GRADE_WEIGHTS[grades[sc["n"]]]/total_w for sc in scenarios}

        # Correlation penalty
        if q_idx > 0:
            prices_dict = {sc["n"]: [x["price"] for x in sc["h"][:lookback_bar]]
                           for sc in scenarios}
            for i, sc_i in enumerate(scenarios):
                for j, sc_j in enumerate(scenarios):
                    if i >= j: continue
                    if (grades[sc_i["n"]] in (AssetGrade.A_PLUS, AssetGrade.A) and
                        grades[sc_j["n"]] in (AssetGrade.A_PLUS, AssetGrade.A)):
                        corr = _correlation(prices_dict[sc_i["n"]], prices_dict[sc_j["n"]])
                        if corr > 0.70:
                            loser = sc_j["n"] if composites.get(sc_i["n"],0) >= composites.get(sc_j["n"],0) else sc_i["n"]
                            alloc[loser] *= 0.60

            total_a = sum(alloc.values())
            for k in alloc: alloc[k] /= total_a

        quarterly_allocs.append(alloc)

        q_label = f"Q{q_idx+1} (bar {q_start}-{q_end if q_end else 'end'})"
        grade_summary = " ".join(f"{sc['n'][:4]}={grades[sc['n']].value}" for sc in scenarios[:6])
        print(f"  {q_label}: {grade_summary}...")

    # ═══ COMPUTE PORTFOLIO RETURNS ═══
    # For each strategy, compute weighted return across quarters

    # Get quarterly price returns for each asset
    def quarterly_bh(h, q_start, q_end):
        """B&H return for a quarter."""
        end = min(q_end if q_end else len(h)-1, len(h)-1)
        start = min(q_start, len(h)-1)
        if start >= end: return 0
        return h[end]["price"] / h[start]["price"] - 1

    def quarterly_wt(eq_curve, q_start, q_end):
        """WT return for a quarter from equity curve."""
        # equity curve starts at bar=warmup, so offset
        warmup = 20
        s = q_start - warmup + 1  # +1 because eq_curve[0] = initial capital
        e = (q_end if q_end else 252) - warmup + 1
        s = max(s, 0)
        e = min(e, len(eq_curve)-1)
        if s >= e or eq_curve[s] == 0: return 0
        return eq_curve[e] / eq_curve[s] - 1

    # Strategy 1: Equal Weight (static)
    ew_portfolio_value = portfolio_capital
    for q_idx, (q_start, q_end) in enumerate(quarters):
        q_ret = statistics.mean(
            quarterly_wt(asset_results[sc["n"]]["equity_curve"], q_start, q_end)
            for sc in scenarios
        )
        ew_portfolio_value *= (1 + q_ret)

    # Strategy 2: Static grade-weight (v2)
    static_alloc = quarterly_allocs[1]  # use bar-120 grades (same as v2)
    static_portfolio_value = portfolio_capital
    for q_idx, (q_start, q_end) in enumerate(quarters):
        q_ret = sum(
            static_alloc[sc["n"]] * quarterly_wt(asset_results[sc["n"]]["equity_curve"], q_start, q_end)
            for sc in scenarios
        )
        static_portfolio_value *= (1 + q_ret)

    # Strategy 3: Dynamic rebalance
    dyn_portfolio_value = portfolio_capital
    for q_idx, (q_start, q_end) in enumerate(quarters):
        alloc = quarterly_allocs[q_idx]
        q_ret = sum(
            alloc[sc["n"]] * quarterly_wt(asset_results[sc["n"]]["equity_curve"], q_start, q_end)
            for sc in scenarios
        )
        dyn_portfolio_value *= (1 + q_ret)

    # B&H
    bh_portfolio_value = portfolio_capital
    for q_idx, (q_start, q_end) in enumerate(quarters):
        q_ret = statistics.mean(
            quarterly_bh(sc["h"], q_start, q_end)
            for sc in scenarios
        )
        bh_portfolio_value *= (1 + q_ret)

    # Also simple full-year calculations
    ew_simple = portfolio_capital * (1 + statistics.mean(
        asset_results[sc["n"]]["total_return"] for sc in scenarios))
    static_simple = portfolio_capital * (1 + sum(
        static_alloc[sc["n"]] * asset_results[sc["n"]]["total_return"]
        for sc in scenarios))

    ew_ret = ew_simple/portfolio_capital - 1
    static_ret = static_simple/portfolio_capital - 1
    dyn_ret = dyn_portfolio_value/portfolio_capital - 1
    bh_ret = statistics.mean(asset_results[sc["n"]]["bh"] for sc in scenarios)

    print(f"\n" + "="*100)
    print(f"  PORTFOLIO RESULTS ($100,000)")
    print("="*100)
    print(f"\n  {'Strategy':<45} {'Return':>10} {'$ P&L':>12} {'Alpha':>10}")
    print("  " + "-"*85)
    print(f"  B&H Equal Weight                            {bh_ret:>+9.1%} ${portfolio_capital*bh_ret:>+10,.0f}")
    print(f"  WT v7 Equal Weight                          {ew_ret:>+9.1%} ${portfolio_capital*ew_ret:>+10,.0f} {ew_ret-bh_ret:>+9.1%}")
    print(f"  WT v7 Static Grade-Weight (v2)              {static_ret:>+9.1%} ${portfolio_capital*static_ret:>+10,.0f} {static_ret-bh_ret:>+9.1%}")
    print(f"  >> WT v7 Dynamic Rebalance + Corr (v3b)     {dyn_ret:>+9.1%} ${portfolio_capital*dyn_ret:>+10,.0f} {dyn_ret-bh_ret:>+9.1%}")

    improvement = dyn_ret - static_ret
    print(f"\n  Dynamic vs Static:  {improvement:+.2%}")
    print(f"  Dynamic vs Equal:   {dyn_ret-ew_ret:+.2%}")

    if dyn_ret > static_ret:
        print(f"\n  Dynamic rebalance WINS!")
    elif static_ret > ew_ret:
        print(f"\n  Static grade-weight still best (rebalance noise hurts)")
    print("="*100)

if __name__ == "__main__":
    asyncio.run(main())
