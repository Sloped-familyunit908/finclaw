"""
WhaleTrader Portfolio v2 — GRADE-BASED CAPITAL ALLOCATION
==========================================================
Key insight from v1: don't FILTER assets by grade, instead
use grade to ALLOCATE more capital to high-grade assets.

F-grade assets still get traded (bear strategy works!),
but with minimal capital allocation.
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

async def run_wt(h, capital=10000):
    bt = BacktesterV7(initial_capital=capital)
    r = await bt.run("T","v7",h)
    return r.total_return

async def main():
    print("\n" + "="*100)
    print("  WhaleTrader Portfolio v2 -- GRADE-BASED CAPITAL ALLOCATION")
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

    # Evaluate at bar 120 (half-year of data)
    print(f"\n  Asset grades (120-bar lookback):")
    for sc in scenarios:
        prices = [x["price"] for x in sc["h"][:120]]
        vols = [x.get("volume",0) for x in sc["h"][:120]]
        score = selector.score_asset(prices, vols)
        sc["grade"] = score.grade
        sc["composite"] = score.composite

    # ═══ ALLOCATION STRATEGIES ═══
    # Grade-based weights (don't zero out any asset!)
    GRADE_WEIGHTS = {
        AssetGrade.A_PLUS: 5.0,
        AssetGrade.A: 3.0,
        AssetGrade.B: 2.0,
        AssetGrade.C: 1.0,
        AssetGrade.F: 0.5,  # Still get some capital!
    }

    total_weight = sum(GRADE_WEIGHTS.get(sc["grade"], 1.0) for sc in scenarios)
    grade_alloc = {}
    for sc in scenarios:
        w = GRADE_WEIGHTS.get(sc["grade"], 1.0) / total_weight
        grade_alloc[sc["n"]] = w

    # Run WT on each asset with allocated capital
    print(f"\n  {'Asset':<10} {'Grade':>5} {'Alloc':>7} {'Capital':>10} | {'B&H':>7} {'v7_ret':>7} {'v7_alpha':>8} | {'$ P&L':>10}")
    print("  " + "-"*85)

    total_bh = 0; total_ew = 0; total_grade = 0; total_ew_bh = 0

    for sc in scenarios:
        h = sc["h"]
        bh = h[-1]["price"]/h[0]["price"]-1

        # Equal weight
        ew_capital = portfolio_capital / N
        ew_ret = await run_wt(h, ew_capital)

        # Grade-weighted
        grade_capital = portfolio_capital * grade_alloc[sc["n"]]
        grade_ret = await run_wt(h, grade_capital)

        ew_pnl = ew_capital * ew_ret
        grade_pnl = grade_capital * grade_ret

        total_bh += bh * (1/N)  # equal-weight B&H
        total_ew += ew_pnl
        total_grade += grade_pnl
        total_ew_bh += ew_capital * bh

        print(f"  {sc['n']:<10} {sc['grade'].value:>5} {grade_alloc[sc['n']]:>6.0%} "
              f"${grade_capital:>9,.0f} | {bh:>+6.1%} {ew_ret:>+6.1%} {ew_ret-bh:>+7.1%} | "
              f"EW ${ew_pnl:>+8,.0f}  GW ${grade_pnl:>+8,.0f}")

    ew_total_ret = total_ew / portfolio_capital
    grade_total_ret = total_grade / portfolio_capital

    print(f"\n" + "="*100)
    print(f"  PORTFOLIO SUMMARY ($100,000 initial)")
    print("="*100)
    print(f"\n  {'Strategy':<35} {'Return':>10} {'$ P&L':>12} {'Alpha vs B&H':>12}")
    print("  " + "-"*75)
    print(f"  B&H Equal Weight                  {total_bh:>+9.1%} ${total_ew_bh:>+10,.0f}")
    print(f"  WT v7 Equal Weight                {ew_total_ret:>+9.1%} ${total_ew:>+10,.0f} {ew_total_ret-total_bh:>+11.1%}")
    print(f"  >> WT v7 Grade-Weighted           {grade_total_ret:>+9.1%} ${total_grade:>+10,.0f} {grade_total_ret-total_bh:>+11.1%}")

    improvement = grade_total_ret - ew_total_ret
    print(f"\n  Grade-Weighted vs Equal Weight: {improvement:+.2%} "
          f"(${portfolio_capital*(improvement):+,.0f})")

    if improvement > 0:
        print(f"\n  Stock selection ADDS value!")
    else:
        print(f"\n  Stock selection hurts. Equal weight wins.")

    print("="*100)

if __name__ == "__main__":
    asyncio.run(main())
