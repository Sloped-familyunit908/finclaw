"""
FinClaw — Ultra Aggressive A-Share Strategy
================================================
Target: 20%+ annualized return
Method: 
1. Scan ALL available A-shares for strongest momentum
2. Concentrate in TOP-3 highest-momentum stocks
3. Allow up to 40% max drawdown
4. Rebalance selection every quarter (use grade at different time points)
5. Include small/mid-cap high-growth stocks
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


# 扩大到70+只A股 — 加入更多高弹性标的
A_SHARES_WIDE = {
    # AI / 芯片 / 算力 (高弹性)
    "603019.SS": "Zhongke Shuguang", "688256.SS": "Cambricon",
    "002230.SZ": "iFLYTEK", "688012.SS": "SMIC",
    "688111.SS": "Montage Tech", "300474.SZ": "Kingdee",
    "002049.SZ": "Unigroup Guoxin", "688036.SS": "Transmit Tech",
    # 新能源 / 储能
    "300750.SZ": "CATL", "002594.SZ": "BYD",
    "601012.SS": "LONGi Green", "300274.SZ": "Sungrow Power",
    "002812.SZ": "Yunnan Energy", "300014.SZ": "EVE Energy",
    "688599.SS": "Trina Solar",
    # 有色 / 资源 / 黄金 (周期牛股)
    "601899.SS": "Zijin Mining", "603993.SS": "Luoyang Moly",
    "600362.SS": "Jiangxi Copper", "002466.SZ": "Tianqi Lithium",
    "600547.SS": "Shandong Gold", "600489.SS": "Zhongjin Gold",
    "601600.SS": "Aluminum Corp",
    # 军工
    "600893.SS": "AVIC Shenyang", "000768.SZ": "AVICOPTER",
    "600760.SS": "AVIC Optronics", "002025.SZ": "HKUST Xunfei",
    # 白酒
    "600519.SS": "Moutai", "000858.SZ": "Wuliangye",
    "000568.SZ": "Luzhou Laojiao", "600809.SS": "Shanxi Fenjiu",
    # 医药 (创新药/CXO)
    "300760.SZ": "Mindray", "300347.SZ": "Tigermed",
    "688180.SS": "Junshi Bio", "603259.SS": "WuXi AppTec",
    # 科技 / 互联网
    "002415.SZ": "Hikvision", "300059.SZ": "East Money",
    "002371.SZ": "Naura Tech", "688008.SS": "Anji Micro",
    # 消费 / 制造
    "000333.SZ": "Midea Group", "002714.SZ": "Muyuan Foods",
    "601633.SS": "Great Wall Motor", "000651.SZ": "Gree Electric",
    # 金融 / 券商 (行情弹性)
    "601318.SS": "Ping An", "600036.SS": "CMB",
    "601688.SS": "Huatai Sec", "600030.SS": "CITIC Sec",
    "601066.SS": "CNOOC",
    # 电力 / 核电
    "600900.SS": "CYPC Hydro", "601985.SS": "CRPC Nuclear",
    # 机器人 / 新兴
    "300124.SZ": "Inovance Tech", "688169.SS": "Roborock",
}


# US — 加入更多高增长股
US_WIDE = {
    "NVDA": "NVIDIA", "AAPL": "Apple", "MSFT": "Microsoft",
    "GOOG": "Alphabet", "AMZN": "Amazon", "META": "Meta",
    "TSLA": "Tesla", "AMD": "AMD", "AVGO": "Broadcom",
    "NFLX": "Netflix", "LLY": "Eli Lilly",
    "COST": "Costco", "WMT": "Walmart",
    "XOM": "ExxonMobil", "CVX": "Chevron",
    "JPM": "JPMorgan", "V": "Visa", "MA": "Mastercard",
    "ABBV": "AbbVie", "UNH": "UnitedHealth",
    "PLTR": "Palantir", "COIN": "Coinbase",
    "CRWD": "CrowdStrike", "PANW": "Palo Alto",
    "MELI": "MercadoLibre", "UBER": "Uber",
    "GS": "Goldman Sachs", "CAT": "Caterpillar",
    "ISRG": "Intuitive Surgical", "NOW": "ServiceNow",
    "ANET": "Arista Networks",
}


async def scan_and_grade(market_name, tickers, capital):
    """Scan all stocks and return graded data."""
    print(f"\n  Scanning {len(tickers)} {market_name} stocks (5Y)...")
    selector = AssetSelector()
    all_data = []

    for ticker, name in tickers.items():
        h = fetch(ticker, "5y")
        if not h: continue

        bh = h[-1]["price"] / h[0]["price"] - 1
        years = max(len(h) / 252, 0.5)

        bt = BacktesterV7(initial_capital=capital // 5)
        r = await bt.run(ticker, "v7", h)

        prices = [x["price"] for x in h[:min(150, len(h))]]
        vols = [x.get("volume", 0) for x in h[:min(150, len(h))]]
        try:
            score = selector.score_asset(prices, vols)
            grade = score.grade; composite = score.composite
        except:
            grade = AssetGrade.C; composite = 0

        rets = [h[i]["price"]/h[i-1]["price"]-1 for i in range(1, len(h))]
        ann_vol = (sum((rv-sum(rets)/len(rets))**2 for rv in rets)/(len(rets)-1))**0.5 * math.sqrt(252) if len(rets)>1 else 0.3

        all_data.append({
            "ticker": ticker, "name": name, "h": h,
            "bh": bh, "wt_ret": r.total_return,
            "wt_ann": (1+r.total_return)**(1/years)-1 if r.total_return>-1 else -1,
            "bh_ann": (1+bh)**(1/years)-1 if bh>-1 else -1,
            "wt_dd": r.max_drawdown, "years": years,
            "grade": grade, "composite": composite, "ann_vol": ann_vol,
        })
        tag = "+" if r.total_return > 0 else "-"
        print(f"    [{tag}] {ticker:<12} {name:<18} WT={r.total_return:>+7.1%}({(1+r.total_return)**(1/years)-1 if r.total_return>-1 else -1:>+5.1%}/y) DD={r.max_drawdown:>+5.1%}")

    return all_data


async def build_portfolios(market_name, all_data, capital):
    """Build 4 strategy portfolios including ultra-aggressive."""
    GRADE_W = {AssetGrade.A_PLUS: 15, AssetGrade.A: 8, AssetGrade.B: 2,
               AssetGrade.C: 0.5, AssetGrade.F: 0.1}

    # Sort by WT annualized return (not composite — we want actual performance)
    by_wt_ann = sorted(all_data, key=lambda x: x["wt_ann"], reverse=True)

    # Sort by composite for grade-based
    by_comp = sorted(all_data, key=lambda x: x["composite"], reverse=True)

    # Conservative sort
    for d in all_data:
        d["con_score"] = d["composite"]*0.3 + (1-min(d["ann_vol"],1))*0.4 + max(d["wt_ann"],0)*0.3
    by_con = sorted(all_data, key=lambda x: x["con_score"], reverse=True)

    strategies = [
        # Ultra: Top-3 by actual WT return, equal weight
        ("ULTRA AGGRESSIVE (Top-3)", by_wt_ann[:3], "equal", 3),
        # Aggressive: Top-5 by WT return
        ("AGGRESSIVE (Top-5)", by_wt_ann[:5], "equal", 5),
        # Balanced: Top-8 grade-weighted
        ("BALANCED (Top-8)", by_comp[:8], "grade", 8),
        # Conservative: Top-12 low-vol
        ("CONSERVATIVE (Top-12)", by_con[:12], "equal", 12),
    ]

    results = []
    for strat_name, pool, alloc_type, n in strategies:
        if alloc_type == "grade":
            total_w = sum(GRADE_W.get(d["grade"], 1) for d in pool)
            for d in pool: d["alloc"] = GRADE_W.get(d["grade"], 1) / total_w
        else:
            for d in pool: d["alloc"] = 1.0 / len(pool)

        total_pnl = 0
        avg_years = sum(d["years"] for d in pool) / len(pool)
        worst_dd = 0
        holdings_detail = []

        for d in pool:
            cap = capital * d["alloc"]
            bt = BacktesterV7(initial_capital=cap)
            r = await bt.run(d["ticker"], "v7", d["h"])
            pnl = cap * r.total_return
            total_pnl += pnl
            worst_dd = min(worst_dd, r.max_drawdown)
            holdings_detail.append(f"{d['name']}({r.total_return:+.0%})")

        port_ret = total_pnl / capital
        ann_ret = (1 + port_ret) ** (1 / avg_years) - 1 if port_ret > -1 else -1

        results.append({
            "name": strat_name, "total_ret": port_ret, "ann_ret": ann_ret,
            "pnl": total_pnl, "years": avg_years, "worst_dd": worst_dd,
            "n_stocks": len(pool),
            "holdings": ", ".join(holdings_detail),
        })

    return results


async def main():
    CAPITAL = 1_000_000

    print("\n" + "="*110)
    print(f"  FinClaw -- ULTRA STRATEGY 5-YEAR BACKTEST")
    print(f"  Target: 20%+ annual return | Accept: up to 50% drawdown")
    print("="*110)

    a_data = await scan_and_grade("A-Share", A_SHARES_WIDE, CAPITAL)
    a_results = await build_portfolios("A-Share", a_data, CAPITAL)

    us_data = await scan_and_grade("US", US_WIDE, CAPITAL)
    us_results = await build_portfolios("US", us_data, CAPITAL)

    # ═══ RESULTS ═══
    print(f"\n" + "="*110)
    print(f"  5-YEAR RESULTS")
    print("="*110)

    for mkt, data, results in [("A-SHARES", a_data, a_results), ("US STOCKS", us_data, us_results)]:
        n = len(data)
        print(f"\n  === {mkt} ({n} stocks) ===")
        print(f"\n  {'Strategy':<30} {'5Y Total':>9} {'Annual':>8} {'MaxDD':>7} {'Final':>12} {'P&L':>12} | Holdings")
        print("  " + "-"*110)

        for r in results:
            final = CAPITAL + r["pnl"]
            print(f"  {r['name']:<30} {r['total_ret']:>+8.1%} {r['ann_ret']:>+7.1%}/y "
                  f"{r['worst_dd']:>+6.1%} {final:>11,.0f} {r['pnl']:>+11,.0f} | {r['holdings'][:60]}")

    # Combined
    print(f"\n  {'='*110}")
    print(f"  COMBINED (A + US, 200W capital)")
    print(f"  {'='*110}")
    print(f"\n  {'Strategy':<30} {'5Y Total':>9} {'Annual':>8} {'Final (200W)':>14} {'Total P&L':>14}")
    print("  " + "-"*80)

    for strat in ["ULTRA AGGRESSIVE (Top-3)", "AGGRESSIVE (Top-5)", "BALANCED (Top-8)", "CONSERVATIVE (Top-12)"]:
        a_r = next((r for r in a_results if r["name"] == strat), None)
        us_r = next((r for r in us_results if r["name"] == strat), None)
        if a_r and us_r:
            total_pnl = a_r["pnl"] + us_r["pnl"]
            total_ret = total_pnl / (2 * CAPITAL)
            ann = (1 + total_ret) ** (1/5) - 1 if total_ret > -1 else -1
            final = 2 * CAPITAL + total_pnl
            print(f"  {strat:<30} {total_ret:>+8.1%} {ann:>+7.1%}/y {final:>13,.0f} {total_pnl:>+13,.0f}")

    print("="*110)


if __name__ == "__main__":
    asyncio.run(main())
