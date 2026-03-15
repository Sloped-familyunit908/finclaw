"""
WhaleTrader — Dynamic Quarterly Rebalance + Extended Master Strategies
======================================================================
Key improvements:
1. QUARTERLY REBALANCE: Re-grade and reallocate every 63 bars (~1 quarter)
2. EXTENDED UNIVERSE: 100+ stocks (US + A-shares)
3. NEW MASTERS: Cathie Wood (ARK), Jim Simons (Renaissance), Ray Dalio (improved)
4. COMPREHENSIVE STRATEGY: Full buy/hold/rebalance/adjust cycle

Portfolio lifecycle:
  Q1: Grade all stocks → select → allocate → enter
  Q2: Re-grade → drop losers → add new winners → rebalance
  Q3: Same
  Q4: Same → year-end report
"""
import asyncio, math, sys, os, random
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
        df = yf.Ticker(ticker).history(period=period)
        if df.empty or len(df) < 100: return None
        return [{"date": idx.to_pydatetime(), "price": float(row["Close"]),
                 "volume": float(row["Volume"])} for idx, row in df.iterrows()]
    except:
        return None


# ═══ MEGA UNIVERSE: 120+ stocks ═══
US_MEGA = {
    # AI / Semis
    "NVDA":"NVIDIA","AVGO":"Broadcom","AMD":"AMD","ANET":"Arista","MRVL":"Marvell",
    "QCOM":"Qualcomm","MU":"Micron","LRCX":"Lam Research","KLAC":"KLA Corp",
    # Big Tech
    "AAPL":"Apple","MSFT":"Microsoft","GOOG":"Alphabet","AMZN":"Amazon","META":"Meta",
    "TSLA":"Tesla","NFLX":"Netflix","CRM":"Salesforce","ORCL":"Oracle",
    # Growth / ARK-style (Cathie Wood favorites)
    "PLTR":"Palantir","COIN":"Coinbase","ROKU":"Roku","SQ":"Block","SHOP":"Shopify",
    "DKNG":"DraftKings","PATH":"UiPath","RBLX":"Roblox","U":"Unity",
    "CRSP":"CRISPR Therapeutics","BEAM":"Beam Therapeutics",
    # Healthcare
    "LLY":"Eli Lilly","UNH":"UnitedHealth","ABBV":"AbbVie","MRK":"Merck",
    "ISRG":"Intuitive Surg","DXCM":"DexCom",
    # Consumer
    "COST":"Costco","WMT":"Walmart","KO":"Coca-Cola","PG":"P&G","PEP":"PepsiCo",
    # Energy
    "XOM":"ExxonMobil","CVX":"Chevron","OXY":"Occidental",
    # Finance
    "JPM":"JPMorgan","GS":"Goldman","V":"Visa","MA":"Mastercard","BAC":"BofA",
    # Industrial
    "CAT":"Caterpillar","DE":"John Deere","GE":"GE Aerospace","LMT":"Lockheed",
    # Cybersecurity
    "CRWD":"CrowdStrike","PANW":"Palo Alto","FTNT":"Fortinet",
}

A_MEGA = {
    # AI/芯片
    "688256.SS":"Cambricon","603019.SS":"Zhongke Shuguang","688012.SS":"SMIC",
    "002230.SZ":"iFLYTEK","002371.SZ":"Naura Tech","688008.SS":"Anji Micro",
    "300474.SZ":"Kingdee","688111.SS":"Montage Tech",
    # 新能源
    "300750.SZ":"CATL","002594.SZ":"BYD","300274.SZ":"Sungrow Power",
    "002812.SZ":"Yunnan Energy","601012.SS":"LONGi Green",
    "300014.SZ":"EVE Energy","688599.SS":"Trina Solar",
    # 有色/资源
    "601899.SS":"Zijin Mining","603993.SS":"Luoyang Moly","600362.SS":"Jiangxi Copper",
    "600547.SS":"Shandong Gold","600489.SS":"Zhongjin Gold","601600.SS":"Aluminum Corp",
    "002466.SZ":"Tianqi Lithium",
    # 军工
    "600893.SS":"AVIC Shenyang","000768.SZ":"AVICOPTER","600760.SS":"AVIC Optronics",
    # 消费/白酒
    "600519.SS":"Moutai","000858.SZ":"Wuliangye","000568.SZ":"Luzhou Laojiao",
    "600809.SS":"Shanxi Fenjiu","002304.SZ":"Yanghe",
    # 金融
    "601318.SS":"Ping An","600036.SS":"CMB","601688.SS":"Huatai Sec",
    "600030.SS":"CITIC Sec","601066.SS":"CNOOC",
    # 医药
    "300760.SZ":"Mindray","300347.SZ":"Tigermed","603259.SS":"WuXi AppTec",
    # 科技/消费
    "002415.SZ":"Hikvision","300059.SZ":"East Money","000333.SZ":"Midea Group",
    "300124.SZ":"Inovance Tech","601633.SS":"Great Wall Motor",
    "600900.SS":"CYPC Hydro","601985.SS":"CRPC Nuclear",
    "002714.SZ":"Muyuan Foods","000651.SZ":"Gree Electric",
    # 机器人/新兴
    "688169.SS":"Roborock","002049.SZ":"Unigroup Guoxin",
}


def _compute_metrics(prices, years):
    """Compute comprehensive metrics for a stock."""
    n = len(prices)
    rets = [prices[i]/prices[i-1]-1 for i in range(1, n)]
    ann_vol = (sum((r-sum(rets)/len(rets))**2 for r in rets)/(len(rets)-1))**0.5*math.sqrt(252) if len(rets)>1 else 0.3

    # Momentum at different horizons
    mom_1m = prices[-1]/prices[max(0,n-21)]-1 if n>21 else 0
    mom_3m = prices[-1]/prices[max(0,n-63)]-1 if n>63 else mom_1m
    mom_6m = prices[-1]/prices[max(0,n-126)]-1 if n>126 else mom_3m
    mom_1y = prices[-1]/prices[max(0,n-252)]-1 if n>252 else mom_6m

    # CAGR
    total_ret = prices[-1]/prices[0]-1
    cagr = (1+total_ret)**(1/max(years,0.5))-1 if total_ret>-1 else -1

    # Max drawdown from peak
    peak = prices[0]; max_dd = 0
    for p in prices:
        peak = max(peak, p); max_dd = min(max_dd, (p-peak)/peak)

    # Sharpe-like (return/vol)
    sharpe_approx = cagr / max(ann_vol, 0.05) if cagr > 0 else cagr * 2

    return {
        "ann_vol": ann_vol, "mom_1m": mom_1m, "mom_3m": mom_3m,
        "mom_6m": mom_6m, "mom_1y": mom_1y, "cagr": cagr,
        "max_dd": max_dd, "sharpe": sharpe_approx, "total_ret": total_ret,
    }


# ═══ MASTER STRATEGY DEFINITIONS ═══

def select_cathie_wood(data):
    """Cathie Wood / ARK: Disruptive innovation, high conviction, 5-year horizon.
    Loves: AI, genomics, fintech, autonomous, space. High vol = opportunity."""
    innovation_keywords = ["nvidia","broadcom","palantir","coinbase","block","roblox",
        "crispr","beam","roku","uipath","unity","cambricon","smic","iflytek","naura",
        "catl","byd","sungrow","kingdee","arista","tesla","draftking","path"]
    innovators = [d for d in data if any(kw in d["name"].lower() for kw in innovation_keywords)]
    if len(innovators) < 5:
        innovators = sorted(data, key=lambda x: x["metrics"]["mom_1y"], reverse=True)[:10]
    # Sort by 1Y momentum (she doubles down on winners)
    return sorted(innovators, key=lambda x: x["metrics"]["mom_1y"], reverse=True)[:6]


def select_simons(data):
    """Jim Simons / Renaissance: Pure quant. Highest Sharpe ratio, statistical edge.
    No narratives — only numbers."""
    return sorted(data, key=lambda x: x["metrics"]["sharpe"], reverse=True)[:8]


def select_soros_v2(data):
    """Soros enhanced: Reflexivity + macro. Strong trend + accelerating momentum.
    Key: momentum is ACCELERATING (3M > 6M > 12M in momentum terms)."""
    candidates = []
    for d in data:
        m = d["metrics"]
        # Momentum acceleration check
        accel = (m["mom_3m"] > m["mom_6m"] * 0.6 and  # 3M momentum > 60% of 6M
                 m["mom_1m"] > 0.03 and  # Recent 1M positive
                 m["mom_1y"] > 0.15)  # At least 15% annual momentum
        if accel:
            d["soros_score"] = m["mom_1m"]*0.4 + m["mom_3m"]*0.3 + m["mom_1y"]*0.3
            candidates.append(d)
    if len(candidates) < 3:
        candidates = sorted(data, key=lambda x: x["metrics"]["mom_1y"], reverse=True)[:5]
        for d in candidates: d["soros_score"] = d["metrics"]["mom_1y"]
    return sorted(candidates, key=lambda x: x.get("soros_score",0), reverse=True)[:5]


def select_buffett_v2(data):
    """Buffett v2: Wide moat + margin of safety. Low vol, steady CAGR, deep dip recovery."""
    for d in data:
        m = d["metrics"]
        recovery = max(-m["max_dd"] - 0.20, 0)  # Bonus for >20% drawdown recovery
        d["buffett_score"] = m["cagr"]*0.35 + (1-min(m["ann_vol"],1))*0.30 + recovery*0.20 + max(m["sharpe"],0)*0.15
    return sorted(data, key=lambda x: x.get("buffett_score",0), reverse=True)[:8]


def select_lynch_v2(data):
    """Lynch v2: PEG-style — growth rate relative to volatility. Boring winners."""
    for d in data:
        m = d["metrics"]
        d["lynch_score"] = max(m["cagr"],0) / max(m["ann_vol"],0.10)
    return sorted(data, key=lambda x: x.get("lynch_score",0), reverse=True)[:7]


def select_druckenmiller_v2(data):
    """Druckenmiller v2: Macro momentum. "When you see it, bet BIG."
    Top-3 by absolute WT performance (proven winners)."""
    return sorted(data, key=lambda x: x.get("wt_ann",0), reverse=True)[:3]


def select_dalio_v2(data):
    """Dalio v2: Risk parity with correlation filter."""
    # Take top-15 by composite, then filter for diversity
    by_comp = sorted(data, key=lambda x: x.get("composite",0), reverse=True)[:15]
    # Simple diversity: alternate between sectors (using volatility spread)
    selected = []
    vols_seen = set()
    for d in by_comp:
        vol_bucket = round(d["metrics"]["ann_vol"], 1)
        if vol_bucket not in vols_seen or len(selected) < 3:
            selected.append(d)
            vols_seen.add(vol_bucket)
        if len(selected) >= 10: break
    return selected


MASTER_STRATEGIES = {
    "cathie_wood": ("Cathie Wood / ARK Innovation", select_cathie_wood, "equal", "VERY HIGH", "20-40%"),
    "simons": ("Jim Simons / Renaissance Quant", select_simons, "equal", "MEDIUM", "15-25%"),
    "soros_v2": ("Soros v2 / Reflexivity Enhanced", select_soros_v2, "equal", "HIGH", "25-35%"),
    "buffett_v2": ("Buffett v2 / Deep Value", select_buffett_v2, "equal", "MEDIUM", "18-28%"),
    "lynch_v2": ("Lynch v2 / Tenbagger Hunter", select_lynch_v2, "equal", "MEDIUM-HIGH", "20-30%"),
    "druckenmiller_v2": ("Druckenmiller v2 / Macro Bet", select_druckenmiller_v2, "equal", "VERY HIGH", "25-40%"),
    "dalio_v2": ("Dalio v2 / Risk Parity Plus", select_dalio_v2, "risk_parity", "LOW-MEDIUM", "12-18%"),
}


async def quarterly_rebalance_backtest(strategy_name, select_fn, alloc_type, all_stocks_data, capital):
    """
    QUARTERLY REBALANCE BACKTEST
    Every ~63 bars, re-evaluate all stocks and rebalance portfolio.
    This simulates a REAL fund manager's workflow.
    """
    # Split all history into quarters
    # Find the minimum common length
    min_len = min(len(d["h"]) for d in all_stocks_data)
    n_quarters = max(min_len // 63, 1)

    portfolio_value = capital
    quarterly_returns = []

    for q in range(n_quarters):
        q_start = q * 63
        q_end = min((q + 1) * 63, min_len)
        if q_end - q_start < 20: continue

        # For selection: use data UP TO q_start (no look-ahead)
        selector = AssetSelector()
        eval_data = []
        for d in all_stocks_data:
            if q_start < 60: continue  # need enough history
            prices = [x["price"] for x in d["h"][:q_start]]
            if len(prices) < 60: continue
            years = len(prices) / 252
            metrics = _compute_metrics(prices, years)

            try:
                score = selector.score_asset(
                    prices[-min(150,len(prices)):],
                    [x.get("volume",0) for x in d["h"][:q_start]][-min(150,len(prices)):]
                )
                grade = score.grade; composite = score.composite
            except:
                grade = AssetGrade.C; composite = 0

            eval_data.append({
                **d, "metrics": metrics, "grade": grade, "composite": composite,
                "wt_ann": metrics["cagr"],
            })

        if not eval_data: continue

        # Select stocks for this quarter
        pool = select_fn(eval_data)
        if not pool: continue

        # Allocate
        GRADE_W = {AssetGrade.A_PLUS:12, AssetGrade.A:6, AssetGrade.B:2, AssetGrade.C:0.5, AssetGrade.F:0.1}
        if alloc_type == "risk_parity":
            for d in pool: d["rp_w"] = 1.0 / max(d["metrics"]["ann_vol"], 0.10)
            total_rp = sum(d["rp_w"] for d in pool)
            for d in pool: d["alloc"] = d["rp_w"] / total_rp
        elif alloc_type == "grade":
            total_w = sum(GRADE_W.get(d["grade"],1) for d in pool)
            for d in pool: d["alloc"] = GRADE_W.get(d["grade"],1) / total_w
        else:
            for d in pool: d["alloc"] = 1.0 / len(pool)

        # Run WT on quarter slice for each holding
        q_pnl = 0
        for d in pool:
            slice_h = d["h"][max(0, q_start-20):q_end]  # include warmup
            if len(slice_h) < 25: continue
            cap = portfolio_value * d["alloc"]
            bt = BacktesterV7(initial_capital=cap)
            try:
                r = await bt.run(d["ticker"], "v7", slice_h)
                q_pnl += cap * r.total_return
            except:
                pass

        q_ret = q_pnl / portfolio_value if portfolio_value > 0 else 0
        portfolio_value += q_pnl
        quarterly_returns.append(q_ret)

    total_ret = portfolio_value / capital - 1
    years = n_quarters * 63 / 252
    ann_ret = (1 + total_ret) ** (1 / max(years, 0.5)) - 1 if total_ret > -1 else -1

    return {
        "strategy": strategy_name,
        "total_ret": total_ret, "ann_ret": ann_ret,
        "final": portfolio_value, "pnl": portfolio_value - capital,
        "years": years, "n_quarters": n_quarters,
        "quarterly_returns": quarterly_returns,
    }


async def main():
    CAPITAL = 1_000_000

    print("\n" + "="*110)
    print("  WhaleTrader — EXTENDED MASTER STRATEGIES + QUARTERLY REBALANCE")
    print("  7 Masters | 100+ Stocks | Dynamic Quarterly Adjustment")
    print("="*110)

    # Phase 1: Load all data
    all_tickers = {**US_MEGA, **A_MEGA}
    print(f"\n  Loading {len(all_tickers)} stocks (5Y data)...")

    all_data = []
    for ticker, name in all_tickers.items():
        h = fetch(ticker, "5y")
        if not h: continue
        prices = [x["price"] for x in h]
        years = len(h) / 252
        metrics = _compute_metrics(prices, years)

        # Full backtest for ranking
        bt = BacktesterV7(initial_capital=CAPITAL//10)
        try:
            r = await bt.run(ticker, "v7", h)
            wt_ret = r.total_return
            wt_ann = (1+wt_ret)**(1/max(years,0.5))-1 if wt_ret>-1 else -1
        except:
            wt_ret = 0; wt_ann = 0

        selector = AssetSelector()
        try:
            score = selector.score_asset(
                [x["price"] for x in h[:min(150,len(h))]],
                [x.get("volume",0) for x in h[:min(150,len(h))]])
            grade = score.grade; composite = score.composite
        except:
            grade = AssetGrade.C; composite = 0

        all_data.append({
            "ticker": ticker, "name": name, "h": h,
            "metrics": metrics, "wt_ret": wt_ret, "wt_ann": wt_ann,
            "grade": grade, "composite": composite,
        })
        tag = "+" if wt_ret > 0 else "-"
        print(f"    [{tag}] {ticker:<12} {name:<20} {wt_ann:>+5.1%}/y vol={metrics['ann_vol']:.0%}")

    N = len(all_data)
    print(f"\n  {N} stocks loaded.\n")

    # Phase 2: Static backtests (full 5Y, no rebalance)
    print("="*110)
    print("  STATIC STRATEGIES (Full 5Y, no rebalance)")
    print("="*110)

    static_results = []
    for key, (name, select_fn, alloc, risk, target) in MASTER_STRATEGIES.items():
        pool = select_fn(all_data)
        if not pool: continue

        GRADE_W = {AssetGrade.A_PLUS:12, AssetGrade.A:6, AssetGrade.B:2, AssetGrade.C:0.5, AssetGrade.F:0.1}
        if alloc == "risk_parity":
            for d in pool: d["rp_w"] = 1.0/max(d["metrics"]["ann_vol"],0.1)
            trp = sum(d["rp_w"] for d in pool); 
            for d in pool: d["alloc"] = d["rp_w"]/trp
        elif alloc == "grade":
            tw = sum(GRADE_W.get(d["grade"],1) for d in pool)
            for d in pool: d["alloc"] = GRADE_W.get(d["grade"],1)/tw
        else:
            for d in pool: d["alloc"] = 1.0/len(pool)

        total_pnl = 0
        avg_years = sum(len(d["h"])/252 for d in pool) / len(pool)
        holdings = []
        for d in pool:
            cap = CAPITAL * d["alloc"]
            bt = BacktesterV7(initial_capital=cap)
            try:
                r = await bt.run(d["ticker"], "v7", d["h"])
                total_pnl += cap * r.total_return
                holdings.append(f"{d['name']}({r.total_return:+.0%})")
            except:
                holdings.append(f"{d['name']}(ERR)")

        port_ret = total_pnl / CAPITAL
        ann = (1+port_ret)**(1/max(avg_years,0.5))-1 if port_ret>-1 else -1

        static_results.append((name, port_ret, ann, risk, target, holdings))

    static_results.sort(key=lambda x: x[2], reverse=True)

    print(f"\n  {'#':<3} {'Strategy':<35} {'5Y Total':>9} {'Annual':>8} {'Risk':<12} | Top Holdings")
    print("  " + "-"*110)
    for i, (name, ret, ann, risk, target, holdings) in enumerate(static_results, 1):
        print(f"  {i:<3} {name:<35} {ret:>+8.1%} {ann:>+7.1%}/y {risk:<12} | {', '.join(holdings[:4])}")

    # Phase 3: Quarterly rebalance backtests
    print(f"\n" + "="*110)
    print("  DYNAMIC STRATEGIES (Quarterly Rebalance)")
    print("="*110)

    dynamic_results = []
    for key, (name, select_fn, alloc, risk, target) in MASTER_STRATEGIES.items():
        print(f"\n  Running {name} with quarterly rebalance...")
        result = await quarterly_rebalance_backtest(name, select_fn, alloc, all_data, CAPITAL)
        dynamic_results.append((name, result, risk, target))
        print(f"    -> {result['total_ret']:+.1%} total ({result['ann_ret']:+.1%}/y) "
              f"over {result['years']:.1f}y, {result['n_quarters']} quarters")

    dynamic_results.sort(key=lambda x: x[1]["ann_ret"], reverse=True)

    print(f"\n  {'#':<3} {'Strategy':<35} {'Total':>9} {'Annual':>8} {'Risk':<12} {'Final':>12}")
    print("  " + "-"*85)
    for i, (name, r, risk, target) in enumerate(dynamic_results, 1):
        print(f"  {i:<3} {name:<35} {r['total_ret']:>+8.1%} {r['ann_ret']:>+7.1%}/y "
              f"{risk:<12} {r['final']:>11,.0f}")

    # Phase 4: Comparison
    print(f"\n" + "="*110)
    print("  STATIC vs DYNAMIC COMPARISON")
    print("="*110)
    print(f"\n  {'Strategy':<35} {'Static Ann':>10} {'Dynamic Ann':>12} {'Better':>8}")
    print("  " + "-"*70)
    for s_name, s_ret, s_ann, _, _, _ in static_results:
        d_match = next((d for d in dynamic_results if d[0]==s_name), None)
        if d_match:
            d_ann = d_match[1]["ann_ret"]
            better = "Dynamic" if d_ann > s_ann else "Static"
            print(f"  {s_name:<35} {s_ann:>+9.1%}/y {d_ann:>+11.1%}/y {better:>8}")

    print("="*110)

if __name__ == "__main__":
    asyncio.run(main())
