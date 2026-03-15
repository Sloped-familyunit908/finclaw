"""
FinClaw — 100万A股实盘模拟
================================
用真实A股数据回测3种风格：
1. 激进型：Top-5集中持仓，高Grade高仓位
2. 均衡型：Top-10分散，Grade加权
3. 保守型：Top-15分散，低波动优先

输入：100万人民币
数据：真实A股1年数据（yfinance）
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


# 扩大A股池 — 覆盖更多行业龙头
A_SHARES_FULL = {
    # AI / 芯片 / 算力
    "603019.SS": "Zhongke Shuguang", "688256.SS": "Cambricon",
    "002230.SZ": "iFLYTEK", "688012.SS": "SMIC",
    "688111.SS": "Montage Tech", "300474.SZ": "Kingdee",
    # 新能源
    "300750.SZ": "CATL", "002594.SZ": "BYD",
    "601012.SS": "LONGi Green", "300274.SZ": "Sungrow Power",
    "002812.SZ": "Yunnan Energy",
    # 有色 / 资源
    "601899.SS": "Zijin Mining", "603993.SS": "Luoyang Moly",
    "600362.SS": "Jiangxi Copper", "002466.SZ": "Tianqi Lithium",
    "600547.SS": "Shandong Gold",
    # 军工
    "600893.SS": "AVIC Shenyang", "000768.SZ": "AVICOPTER",
    "600760.SS": "AVIC Optronics",
    # 白酒
    "600519.SS": "Moutai", "000858.SZ": "Wuliangye",
    "000568.SZ": "Luzhou Laojiao", "002304.SZ": "Yanghe",
    # 金融
    "601318.SS": "Ping An Ins", "600036.SS": "CMB",
    "601688.SS": "Huatai Sec", "600030.SS": "CITIC Sec",
    # 医药
    "300760.SZ": "Mindray", "300347.SZ": "Tigermed",
    "688180.SS": "Junshi Bio", "603259.SS": "WuXi AppTec",
    # 科技 / 消费
    "002415.SZ": "Hikvision", "300059.SZ": "East Money",
    "002714.SZ": "Muyuan Foods", "600809.SS": "Shanxi Fenjiu",
    # 汽车 / 制造
    "601127.SS": "Sai Lung", "000333.SZ": "Midea Group",
    "601633.SS": "Great Wall Motor",
    # 电力 / 基建
    "600900.SS": "CYPC (Hydro)", "601985.SS": "CRPC (Nuclear)",
}


async def main():
    CAPITAL = 1_000_000  # 100万

    print("\n" + "="*110)
    print(f"  FinClaw -- 100W A-SHARE PORTFOLIO SIMULATION")
    print(f"  Capital: RMB {CAPITAL:,.0f} | Data: Real 1Y | 3 Strategies")
    print("="*110)

    # ═══ PHASE 1: Scan all stocks ═══
    print(f"\n  Phase 1: Scanning {len(A_SHARES_FULL)} A-share stocks...")
    selector = AssetSelector()
    all_data = []

    for ticker, name in A_SHARES_FULL.items():
        h = fetch(ticker, "1y")
        if not h:
            continue

        bh = h[-1]["price"] / h[0]["price"] - 1

        # Run backtest
        bt = BacktesterV7(initial_capital=CAPITAL // 10)  # temp sizing
        r = await bt.run(ticker, "v7", h)

        # Grade
        prices = [x["price"] for x in h[:min(150, len(h))]]
        vols = [x.get("volume", 0) for x in h[:min(150, len(h))]]
        try:
            score = selector.score_asset(prices, vols)
            grade = score.grade
            composite = score.composite
        except:
            grade = AssetGrade.C
            composite = 0

        # Volatility (annualized)
        rets = [h[i]["price"]/h[i-1]["price"]-1 for i in range(1, len(h))]
        import math
        ann_vol = (sum((r - sum(rets)/len(rets))**2 for r in rets) / (len(rets)-1)) ** 0.5 * math.sqrt(252) if len(rets) > 1 else 0.3

        all_data.append({
            "ticker": ticker, "name": name, "h": h,
            "bh": bh, "wt_ret": r.total_return, "wt_alpha": r.total_return - bh,
            "wt_dd": r.max_drawdown, "wt_trades": r.total_trades,
            "grade": grade, "composite": composite, "ann_vol": ann_vol,
        })

        tag = "+" if r.total_return > 0 else "-"
        print(f"    [{tag}] {ticker:<12} {name:<18} B&H={bh:>+6.1%} WT={r.total_return:>+6.1%} "
              f"a={r.total_return-bh:>+5.1%} vol={ann_vol:.0%} {grade.value}")

    N = len(all_data)
    print(f"\n  Phase 1 complete: {N} stocks scanned\n")

    # ═══ PHASE 2: Build 3 portfolios ═══
    GRADE_W = {AssetGrade.A_PLUS: 12, AssetGrade.A: 6, AssetGrade.B: 2,
               AssetGrade.C: 0.5, AssetGrade.F: 0.1}

    # --- Strategy 1: AGGRESSIVE (Top-5 by composite, max conviction) ---
    aggressive_pool = sorted(all_data, key=lambda x: x["composite"], reverse=True)[:5]

    # --- Strategy 2: BALANCED (Top-10, grade-weighted) ---
    balanced_pool = sorted(all_data, key=lambda x: x["composite"], reverse=True)[:10]

    # --- Strategy 3: CONSERVATIVE (Top-15, low-vol preference) ---
    # Score = composite * 0.5 + (1 - ann_vol) * 0.5  (balance quality + low risk)
    for d in all_data:
        d["conservative_score"] = d["composite"] * 0.5 + (1 - min(d["ann_vol"], 1.0)) * 0.5
    conservative_pool = sorted(all_data, key=lambda x: x["conservative_score"], reverse=True)[:15]

    strategies = [
        ("AGGRESSIVE (Top-5 Equal)", aggressive_pool, "equal"),
        ("BALANCED (Top-10 Grade-Weighted)", balanced_pool, "grade"),
        ("CONSERVATIVE (Top-15 Low-Vol)", conservative_pool, "equal"),
    ]

    for strat_name, pool, alloc_type in strategies:
        print(f"\n  {'='*100}")
        print(f"  STRATEGY: {strat_name}")
        print(f"  {'='*100}")

        if alloc_type == "grade":
            total_w = sum(GRADE_W.get(d["grade"], 1) for d in pool)
            for d in pool:
                d["alloc"] = GRADE_W.get(d["grade"], 1) / total_w
        else:
            for d in pool:
                d["alloc"] = 1.0 / len(pool)

        total_pnl = 0; total_bh_pnl = 0

        print(f"\n  {'Ticker':<12} {'Name':<18} {'Grade':>5} {'Alloc':>6} {'Capital':>10} | "
              f"{'B&H':>7} {'WT':>7} {'Alpha':>7} | {'P&L':>12}")
        print("  " + "-"*100)

        for d in pool:
            cap = CAPITAL * d["alloc"]

            # Re-run with correct capital
            bt = BacktesterV7(initial_capital=cap)
            r = await bt.run(d["ticker"], "v7", d["h"])
            pnl = cap * r.total_return
            bh_pnl = cap * d["bh"]
            total_pnl += pnl
            total_bh_pnl += bh_pnl

            print(f"  {d['ticker']:<12} {d['name']:<18} {d['grade'].value:>5} {d['alloc']:>5.0%} "
                  f"RMB{cap:>9,.0f} | {d['bh']:>+6.1%} {r.total_return:>+6.1%} "
                  f"{r.total_return-d['bh']:>+6.1%} | RMB{pnl:>+11,.0f}")

        port_ret = total_pnl / CAPITAL
        bh_ret = total_bh_pnl / CAPITAL
        alpha = port_ret - bh_ret

        print(f"\n  RESULT:")
        print(f"    Initial:     RMB {CAPITAL:>12,.0f}")
        print(f"    Final:       RMB {CAPITAL + total_pnl:>12,.0f}")
        print(f"    P&L:         RMB {total_pnl:>+12,.0f} ({port_ret:>+.1%})")
        print(f"    B&H equiv:   RMB {total_bh_pnl:>+12,.0f} ({bh_ret:>+.1%})")
        print(f"    Alpha:       {alpha:>+.1%}")

    # ═══ SUMMARY ═══
    print(f"\n  {'='*100}")
    print(f"  COMPARISON: Which strategy for 100W?")
    print(f"  {'='*100}")
    print(f"\n  {'Strategy':<45} {'Return':>8} {'Final Value':>14} {'Risk':>10}")
    print("  " + "-"*80)

    # Recalculate for summary (simplified)
    for strat_name, pool, alloc_type in strategies:
        if alloc_type == "grade":
            total_w = sum(GRADE_W.get(d["grade"], 1) for d in pool)
            allocs = {d["ticker"]: GRADE_W.get(d["grade"], 1) / total_w for d in pool}
        else:
            allocs = {d["ticker"]: 1.0 / len(pool) for d in pool}

        total_pnl = sum(CAPITAL * allocs[d["ticker"]] * d["wt_ret"] for d in pool)
        port_ret = total_pnl / CAPITAL
        avg_dd = sum(d["wt_dd"] * allocs[d["ticker"]] for d in pool)
        avg_vol = sum(d["ann_vol"] * allocs[d["ticker"]] for d in pool)

        risk_label = "HIGH" if avg_vol > 0.4 else ("MED" if avg_vol > 0.25 else "LOW")
        print(f"  {strat_name:<45} {port_ret:>+7.1%} RMB{CAPITAL+total_pnl:>12,.0f} {risk_label:>10}")

    print(f"\n  B&H benchmark (equal-weight all {N}): "
          f"{sum(d['bh'] for d in all_data)/N:>+.1%}")
    print("="*110)


if __name__ == "__main__":
    asyncio.run(main())
