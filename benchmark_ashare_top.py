"""
WhaleTrader — A股最强选股 2025
================================
扫描A股热门板块，找出过去一年回报最高的股票，
然后用WhaleTrader v7跑回测，找最优组合。

板块覆盖：AI/芯片、新能源、军工、消费、金融、医药、有色金属
"""
import asyncio
import sys, os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.backtester_v7 import BacktesterV7
from agents.signal_engine_v9 import AssetSelector, AssetGrade

try:
    import yfinance as yf
except ImportError:
    print("pip install yfinance"); sys.exit(1)


def fetch(ticker, period="1y"):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        if df.empty or len(df) < 60: return None
        return [{"date": idx.to_pydatetime(), "price": float(row["Close"]),
                 "volume": float(row["Volume"])} for idx, row in df.iterrows()]
    except:
        return None


# A股热门标的 — 按板块分类
A_SHARES = {
    # AI / 算力 / 芯片
    "603019.SS": "Zhongke Shuguang (AI Server)",
    "688256.SS": "Cambricon (AI Chip)",
    "002230.SZ": "iFLYTEK (AI Voice)",
    "300474.SZ": "Kingdee Intl (SaaS)",
    "688111.SS": "Montage Tech (DRAM)",
    "688012.SS": "SMIC (Chip Foundry)",

    # 新能源 / 电池 / 光伏
    "300750.SZ": "CATL (Battery)",
    "002594.SZ": "BYD (EV)",
    "601012.SS": "LONGi Green (Solar)",
    "300274.SZ": "Sungrow Power (Inverter)",
    "002812.SZ": "Yunnan Energy (Separator)",

    # 军工 / 航天
    "600893.SS": "AVIC Shenyang (Fighter Jets)",
    "000768.SZ": "AVICOPTER (Helicopter)",
    "600760.SS": "AVIC Optronics (Defense)",

    # 消费 / 白酒
    "600519.SS": "Kweichow Moutai",
    "000858.SZ": "Wuliangye",
    "000568.SZ": "Luzhou Laojiao",
    "002304.SZ": "Yanghe Brewery",

    # 金融
    "601318.SS": "Ping An Insurance",
    "600036.SS": "China Merchants Bank",
    "601688.SS": "Huatai Securities",

    # 医药 / 创新药
    "300760.SZ": "Mindray Medical",
    "688180.SS": "Junshi Bio (PD-1)",
    "300347.SZ": "Hangzhou Tigermed (CRO)",

    # 有色金属 / 资源
    "601899.SS": "Zijin Mining (Gold/Copper)",
    "603993.SS": "Luoyang Molybdenum",
    "002466.SZ": "Tianqi Lithium",
    "600362.SS": "Jiangxi Copper",

    # 科技 / 互联网
    "002415.SZ": "Hikvision (Security)",
    "300059.SZ": "East Money (Fintech)",
}


async def main():
    print("\n" + "="*110)
    print("  WhaleTrader — A-SHARE TOP PERFORMER SCAN (2024-2025)")
    print("="*110)

    print(f"\n  Scanning {len(A_SHARES)} A-share stocks...\n")

    results = []
    selector = AssetSelector()

    for ticker, name in A_SHARES.items():
        h = fetch(ticker, "1y")
        if not h:
            print(f"  {ticker:<12} {name:<28} SKIP")
            continue

        bh = h[-1]["price"] / h[0]["price"] - 1

        # WhaleTrader v7
        bt = BacktesterV7(initial_capital=100000)
        r = await bt.run(ticker, "v7", h)
        wt_alpha = r.total_return - bh

        # Asset grade
        prices = [x["price"] for x in h[:min(150, len(h))]]
        vols = [x.get("volume", 0) for x in h[:min(150, len(h))]]
        try:
            score = selector.score_asset(prices, vols)
            grade = score.grade.value
            composite = score.composite
        except:
            grade = "?"
            composite = 0

        results.append({
            "ticker": ticker, "name": name, "bh": bh,
            "wt_ret": r.total_return, "wt_alpha": wt_alpha,
            "wt_dd": r.max_drawdown, "wt_trades": r.total_trades,
            "grade": grade, "composite": composite,
        })

        tag = "+" if wt_alpha > 0 else "-"
        print(f"  [{tag}] {ticker:<12} {name:<28} B&H={bh:>+7.1%} | "
              f"WT={r.total_return:>+7.1%} a={wt_alpha:>+6.1%} DD={r.max_drawdown:>+5.1%} "
              f"T={r.total_trades:>2} | {grade}")

    if not results:
        print("  No results."); return

    # ═══ RANKINGS ═══
    print(f"\n" + "="*110)
    print(f"  RANKINGS ({len(results)} stocks)")
    print("="*110)

    # Top 10 by B&H return (what went up most)
    by_bh = sorted(results, key=lambda x: x["bh"], reverse=True)
    print(f"\n  --- TOP 10 by B&H Return (raw market performance) ---")
    for i, r in enumerate(by_bh[:10], 1):
        print(f"  {i:>2}. {r['ticker']:<12} {r['name']:<28} B&H={r['bh']:>+7.1%}")

    # Top 10 by WT return (what WT made most money on)
    by_wt = sorted(results, key=lambda x: x["wt_ret"], reverse=True)
    print(f"\n  --- TOP 10 by WhaleTrader Return ---")
    for i, r in enumerate(by_wt[:10], 1):
        print(f"  {i:>2}. {r['ticker']:<12} {r['name']:<28} WT={r['wt_ret']:>+7.1%} "
              f"(B&H={r['bh']:>+7.1%}) alpha={r['wt_alpha']:>+6.1%}")

    # Top 10 by Alpha (where WT added most value vs B&H)
    by_alpha = sorted(results, key=lambda x: x["wt_alpha"], reverse=True)
    print(f"\n  --- TOP 10 by Alpha (WT value-add vs B&H) ---")
    for i, r in enumerate(by_alpha[:10], 1):
        print(f"  {i:>2}. {r['ticker']:<12} {r['name']:<28} alpha={r['wt_alpha']:>+6.1%} "
              f"(WT={r['wt_ret']:>+7.1%} vs B&H={r['bh']:>+7.1%})")

    # Best risk-adjusted (alpha / |DD|)
    by_risk = sorted(results, key=lambda x: x["wt_alpha"]/max(abs(x["wt_dd"]),0.01), reverse=True)
    print(f"\n  --- TOP 10 by Risk-Adjusted Alpha (alpha/|MaxDD|) ---")
    for i, r in enumerate(by_risk[:10], 1):
        ratio = r["wt_alpha"] / max(abs(r["wt_dd"]), 0.01)
        print(f"  {i:>2}. {r['ticker']:<12} {r['name']:<28} ratio={ratio:>+5.2f} "
              f"alpha={r['wt_alpha']:>+6.1%} DD={r['wt_dd']:>+5.1%}")

    # ═══ OPTIMAL PORTFOLIO ═══
    print(f"\n" + "="*110)
    print(f"  OPTIMAL A-SHARE PORTFOLIO (Grade-weighted)")
    print("="*110)

    GRADE_W = {"A+": 12, "A": 6, "B": 1.5, "C": 0.5, "F": 0.2}
    portfolio_capital = 1000000  # 100万

    valid = [r for r in results if r["grade"] in GRADE_W]
    total_w = sum(GRADE_W.get(r["grade"], 1) for r in valid)

    print(f"\n  {'Ticker':<12} {'Name':<28} {'Grade':>5} {'Alloc':>6} {'Capital':>10} | "
          f"{'B&H':>7} {'WT':>7} {'Alpha':>7} {'$ P&L':>10}")
    print("  " + "-"*110)

    total_pnl = 0; total_bh_pnl = 0
    portfolio_items = sorted(valid, key=lambda x: GRADE_W.get(x["grade"],1), reverse=True)

    for r in portfolio_items:
        w = GRADE_W.get(r["grade"], 1) / total_w
        cap = portfolio_capital * w
        pnl = cap * r["wt_ret"]
        bh_pnl = cap * r["bh"]
        total_pnl += pnl
        total_bh_pnl += bh_pnl
        print(f"  {r['ticker']:<12} {r['name']:<28} {r['grade']:>5} {w:>5.0%} "
              f"${cap:>9,.0f} | {r['bh']:>+6.1%} {r['wt_ret']:>+6.1%} {r['wt_alpha']:>+6.1%} "
              f"${pnl:>+9,.0f}")

    port_ret = total_pnl / portfolio_capital
    bh_ret = total_bh_pnl / portfolio_capital
    print(f"\n  Portfolio: {port_ret:>+.1%} return (${total_pnl:>+,.0f} / ${portfolio_capital:,.0f})")
    print(f"  B&H equal: {bh_ret:>+.1%} (${total_bh_pnl:>+,.0f})")
    print(f"  Alpha: {port_ret - bh_ret:>+.1%}")

    # ═══ TOP-5 CONCENTRATED PORTFOLIO ═══
    print(f"\n  --- TOP-5 CONCENTRATED PORTFOLIO ---")
    top5 = sorted(valid, key=lambda x: x["composite"], reverse=True)[:5]
    cap_each = portfolio_capital / 5
    t5_pnl = sum(cap_each * r["wt_ret"] for r in top5)
    t5_bh = sum(cap_each * r["bh"] for r in top5)
    for r in top5:
        pnl = cap_each * r["wt_ret"]
        print(f"  {r['ticker']:<12} {r['name']:<28} {r['grade']:>3} "
              f"WT={r['wt_ret']:>+7.1%} P&L=${pnl:>+9,.0f}")
    print(f"\n  Top-5 Return: {t5_pnl/portfolio_capital:>+.1%} "
          f"(${t5_pnl:>+,.0f}) vs B&H {t5_bh/portfolio_capital:>+.1%}")

    print("="*110)


if __name__ == "__main__":
    asyncio.run(main())
