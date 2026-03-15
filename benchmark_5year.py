"""
FinClaw — 5-Year Backtest (A-shares & US)
==============================================
Period: 5 years
Capital: 1,000,000 per market
Strategies: Aggressive / Balanced / Conservative
"""
import asyncio, math, sys, os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.backtester_v7 import BacktesterV7
from agents.signal_engine_v9 import AssetSelector, AssetGrade

try:
    import yfinance as yf
except ImportError:
    print("pip install yfinance"); sys.exit(1)


def fetch(ticker, period="5y"):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        if df.empty or len(df) < 200: return None
        return [{"date": idx.to_pydatetime(), "price": float(row["Close"]),
                 "volume": float(row["Volume"])} for idx, row in df.iterrows()]
    except:
        return None


A_SHARES = {
    "603019.SS": "Zhongke Shuguang", "688256.SS": "Cambricon",
    "002230.SZ": "iFLYTEK", "688012.SS": "SMIC",
    "688111.SS": "Montage Tech", "300474.SZ": "Kingdee",
    "300750.SZ": "CATL", "002594.SZ": "BYD",
    "601012.SS": "LONGi Green", "300274.SZ": "Sungrow Power",
    "002812.SZ": "Yunnan Energy",
    "601899.SS": "Zijin Mining", "603993.SS": "Luoyang Moly",
    "600362.SS": "Jiangxi Copper", "002466.SZ": "Tianqi Lithium",
    "600547.SS": "Shandong Gold",
    "600893.SS": "AVIC Shenyang", "000768.SZ": "AVICOPTER",
    "600760.SS": "AVIC Optronics",
    "600519.SS": "Moutai", "000858.SZ": "Wuliangye",
    "000568.SZ": "Luzhou Laojiao", "002304.SZ": "Yanghe",
    "601318.SS": "Ping An Ins", "600036.SS": "CMB",
    "601688.SS": "Huatai Sec", "600030.SS": "CITIC Sec",
    "300760.SZ": "Mindray", "300347.SZ": "Tigermed",
    "688180.SS": "Junshi Bio", "603259.SS": "WuXi AppTec",
    "002415.SZ": "Hikvision", "300059.SZ": "East Money",
    "002714.SZ": "Muyuan Foods", "600809.SS": "Shanxi Fenjiu",
    "000333.SZ": "Midea Group", "601633.SS": "Great Wall Motor",
    "600900.SS": "CYPC Hydro", "601985.SS": "CRPC Nuclear",
    "000651.SZ": "Gree Electric", "601066.SS": "CNOOC",
}

US_STOCKS = {
    "NVDA": "NVIDIA", "AAPL": "Apple", "MSFT": "Microsoft",
    "GOOG": "Alphabet", "AMZN": "Amazon", "META": "Meta",
    "TSLA": "Tesla", "AMD": "AMD", "AVGO": "Broadcom",
    "CRM": "Salesforce", "NFLX": "Netflix", "ADBE": "Adobe",
    "COST": "Costco", "LLY": "Eli Lilly", "UNH": "UnitedHealth",
    "V": "Visa", "MA": "Mastercard", "JPM": "JPMorgan",
    "BAC": "Bank of America", "WMT": "Walmart",
    "PG": "Procter & Gamble", "KO": "Coca-Cola",
    "PEP": "PepsiCo", "MRK": "Merck", "ABBV": "AbbVie",
    "XOM": "ExxonMobil", "CVX": "Chevron",
    "INTC": "Intel", "COIN": "Coinbase", "PLTR": "Palantir",
    "SQ": "Block", "SHOP": "Shopify", "SNOW": "Snowflake",
    "NET": "Cloudflare", "DDOG": "Datadog",
    "GS": "Goldman Sachs", "MS": "Morgan Stanley",
    "CAT": "Caterpillar", "DE": "John Deere",
    "BA": "Boeing",
}


async def scan_market(market_name, tickers, capital):
    print(f"\n  Scanning {len(tickers)} {market_name} stocks (5Y data)...")
    selector = AssetSelector()
    all_data = []

    for ticker, name in tickers.items():
        h = fetch(ticker, "5y")
        if not h:
            continue

        bh = h[-1]["price"] / h[0]["price"] - 1
        years = max(len(h) / 252, 0.5)
        bh_ann = (1 + bh) ** (1 / years) - 1 if bh > -1 else -1

        bt = BacktesterV7(initial_capital=capital // 10)
        r = await bt.run(ticker, "v7", h)
        wt_ann = (1 + r.total_return) ** (1 / years) - 1 if r.total_return > -1 else -1

        prices = [x["price"] for x in h[:min(150, len(h))]]
        vols = [x.get("volume", 0) for x in h[:min(150, len(h))]]
        try:
            score = selector.score_asset(prices, vols)
            grade = score.grade
            composite = score.composite
        except:
            grade = AssetGrade.C
            composite = 0

        rets = [h[i]["price"]/h[i-1]["price"]-1 for i in range(1, len(h))]
        ann_vol = (sum((rv - sum(rets)/len(rets))**2 for rv in rets) / (len(rets)-1)) ** 0.5 * math.sqrt(252) if len(rets) > 1 else 0.3

        all_data.append({
            "ticker": ticker, "name": name, "h": h,
            "bh": bh, "bh_ann": bh_ann,
            "wt_ret": r.total_return, "wt_ann": wt_ann,
            "wt_alpha": r.total_return - bh,
            "wt_dd": r.max_drawdown, "years": years,
            "grade": grade, "composite": composite, "ann_vol": ann_vol,
        })

        tag = "+" if r.total_return > 0 else "-"
        print(f"    [{tag}] {ticker:<12} {name:<18} {years:.1f}y | "
              f"B&H={bh:>+7.1%}({bh_ann:>+5.1%}/y) WT={r.total_return:>+7.1%}({wt_ann:>+5.1%}/y) "
              f"DD={r.max_drawdown:>+5.1%} {grade.value}")

    return all_data


async def run_strategies(market_name, all_data, capital):
    GRADE_W = {AssetGrade.A_PLUS: 12, AssetGrade.A: 6, AssetGrade.B: 2,
               AssetGrade.C: 0.5, AssetGrade.F: 0.1}

    # Sort by composite for selection
    by_comp = sorted(all_data, key=lambda x: x["composite"], reverse=True)

    # Conservative: blend composite + low vol
    for d in all_data:
        d["con_score"] = d["composite"] * 0.4 + (1 - min(d["ann_vol"], 1.0)) * 0.6
    by_con = sorted(all_data, key=lambda x: x["con_score"], reverse=True)

    strategies = [
        ("AGGRESSIVE", by_comp[:5], "equal"),
        ("BALANCED", by_comp[:10], "grade"),
        ("CONSERVATIVE", by_con[:15], "equal"),
    ]

    results = []

    for strat_name, pool, alloc_type in strategies:
        if alloc_type == "grade":
            total_w = sum(GRADE_W.get(d["grade"], 1) for d in pool)
            for d in pool: d["alloc"] = GRADE_W.get(d["grade"], 1) / total_w
        else:
            for d in pool: d["alloc"] = 1.0 / len(pool)

        total_pnl = 0; total_bh_pnl = 0
        avg_years = sum(d["years"] for d in pool) / len(pool)

        for d in pool:
            cap = capital * d["alloc"]
            bt = BacktesterV7(initial_capital=cap)
            r = await bt.run(d["ticker"], "v7", d["h"])
            pnl = cap * r.total_return
            bh_pnl = cap * d["bh"]
            total_pnl += pnl
            total_bh_pnl += bh_pnl

        port_ret = total_pnl / capital
        bh_ret = total_bh_pnl / capital
        ann_ret = (1 + port_ret) ** (1 / avg_years) - 1 if port_ret > -1 else -1
        bh_ann_ret = (1 + bh_ret) ** (1 / avg_years) - 1 if bh_ret > -1 else -1

        holdings = ", ".join(f"{d['name']}" for d in pool[:5])
        if len(pool) > 5: holdings += f"... +{len(pool)-5} more"

        results.append({
            "name": strat_name, "total_ret": port_ret, "ann_ret": ann_ret,
            "bh_ret": bh_ret, "bh_ann": bh_ann_ret, "pnl": total_pnl,
            "years": avg_years, "n_stocks": len(pool), "holdings": holdings,
        })

    return results


async def main():
    CAPITAL = 1_000_000

    print("\n" + "="*110)
    print(f"  FinClaw -- 5-YEAR BACKTEST")
    print(f"  Capital: RMB/USD {CAPITAL:,.0f} per market | Period: 5 Years")
    print("="*110)

    # ═══ A-SHARES ═══
    a_data = await scan_market("A-Share", A_SHARES, CAPITAL)
    a_results = await run_strategies("A-Share", a_data, CAPITAL)

    # ═══ US STOCKS ═══
    us_data = await scan_market("US", US_STOCKS, CAPITAL)
    us_results = await run_strategies("US", us_data, CAPITAL)

    # ═══ FINAL REPORT ═══
    print(f"\n" + "="*110)
    print(f"  5-YEAR RESULTS SUMMARY")
    print("="*110)

    for mkt_name, data, results in [("A-SHARES (CNY)", a_data, a_results),
                                      ("US STOCKS (USD)", us_data, us_results)]:
        n = len(data)
        avg_bh = sum(d["bh"] for d in data) / n if n else 0
        avg_bh_ann = (1 + avg_bh) ** (1 / 5) - 1 if avg_bh > -1 else 0

        print(f"\n  === {mkt_name} ({n} stocks, 5 years) ===")
        print(f"  Market B&H avg: {avg_bh:+.1%} total ({avg_bh_ann:+.1%}/year)")
        print(f"\n  {'Strategy':<25} {'5Y Total':>10} {'Annual':>8} {'Final Value':>14} {'5Y P&L':>14} | {'B&H Total':>10} {'B&H Ann':>8}")
        print("  " + "-"*100)

        for r in results:
            final = CAPITAL + r["pnl"]
            print(f"  {r['name']:<25} {r['total_ret']:>+9.1%} {r['ann_ret']:>+7.1%}/y "
                  f"{final:>13,.0f} {r['pnl']:>+13,.0f} | {r['bh_ret']:>+9.1%} {r['bh_ann']:>+7.1%}/y")
            print(f"    Holdings: {r['holdings']}")

    # Grand total
    print(f"\n  {'='*110}")
    print(f"  GRAND TOTAL (A-shares + US combined, 2M capital)")
    print(f"  {'='*110}")

    for strat in ["AGGRESSIVE", "BALANCED", "CONSERVATIVE"]:
        a_r = next(r for r in a_results if r["name"] == strat)
        us_r = next(r for r in us_results if r["name"] == strat)
        total_pnl = a_r["pnl"] + us_r["pnl"]
        total_ret = total_pnl / (2 * CAPITAL)
        ann = (1 + total_ret) ** (1/5) - 1 if total_ret > -1 else -1
        print(f"  {strat:<25} 5Y={total_ret:>+8.1%} Ann={ann:>+6.1%}/y "
              f"P&L={total_pnl:>+14,.0f} Final={2*CAPITAL+total_pnl:>14,.0f}")

    print("="*110)

if __name__ == "__main__":
    asyncio.run(main())
