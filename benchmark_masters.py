"""
FinClaw — Master Strategies (大师策略)
==========================================
4 investment philosophies, each with distinct risk/return profile:

1. BUFFETT MODE (巴菲特模式)
   - "Be fearful when others are greedy, greedy when others are fearful"
   - Buy quality companies at discount (low P/E moments)
   - Hold through volatility, never panic sell
   - Key: INCREASE position size during drawdowns

2. DALIO ALL-WEATHER (达利欧全天候)
   - Balance across uncorrelated assets
   - Risk parity: equal risk contribution from each asset
   - Rebalance quarterly
   - Key: LOW correlation between holdings

3. DRUCKENMILLER MOMENTUM (德鲁肯米勒动量)
   - "When you see it, bet big"
   - Concentrate in the strongest trend
   - Cut losers fast, let winners run
   - Key: EXTREME concentration, fast rotation

4. SOROS REFLEXIVITY (索罗斯反身性)
   - Market trends reinforce themselves until they break
   - Buy into self-reinforcing loops (AI hype cycle, etc.)
   - Exit when the narrative breaks
   - Key: Narrative + momentum alignment

5. LYNCH TENBAGGER (彼得林奇十倍股)
   - Find "boring" companies with explosive potential
   - Small/mid caps preferred
   - High earnings growth + reasonable valuation
   - Key: Growth rate >> volatility
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


def _corr(prices_a, prices_b, window=60):
    """Pearson correlation of returns."""
    n = min(len(prices_a), len(prices_b))
    if n < 30: return 0
    s = max(0, n - window)
    ra = [prices_a[i]/prices_a[i-1]-1 for i in range(s+1, n)]
    rb = [prices_b[i]/prices_b[i-1]-1 for i in range(s+1, n)]
    if len(ra) < 10: return 0
    ma = sum(ra)/len(ra); mb = sum(rb)/len(rb)
    cov = sum((a-ma)*(b-mb) for a,b in zip(ra,rb)) / len(ra)
    sa = math.sqrt(sum((a-ma)**2 for a in ra)/len(ra))
    sb = math.sqrt(sum((b-mb)**2 for b in rb)/len(rb))
    return cov / (sa * sb) if sa > 0 and sb > 0 else 0


# Combined US + A-share universe
ALL_STOCKS = {
    # US mega
    "NVDA": "NVIDIA", "AVGO": "Broadcom", "ANET": "Arista",
    "NFLX": "Netflix", "LLY": "Eli Lilly", "PLTR": "Palantir",
    "META": "Meta", "GOOG": "Alphabet", "AMD": "AMD",
    "AAPL": "Apple", "MSFT": "Microsoft", "AMZN": "Amazon",
    "TSLA": "Tesla", "COST": "Costco", "WMT": "Walmart",
    "XOM": "ExxonMobil", "CVX": "Chevron", "ABBV": "AbbVie",
    "JPM": "JPMorgan", "V": "Visa", "CAT": "Caterpillar",
    "KO": "Coca-Cola", "PG": "P&G", "ISRG": "Intuitive Surg",
    # A-share
    "688256.SS": "Cambricon", "601899.SS": "Zijin Mining",
    "601600.SS": "Aluminum Corp", "603019.SS": "Zhongke Shuguang",
    "300750.SZ": "CATL", "300274.SZ": "Sungrow Power",
    "002812.SZ": "Yunnan Energy", "603993.SS": "Luoyang Moly",
    "600547.SS": "Shandong Gold", "601985.SS": "CRPC Nuclear",
    "300474.SZ": "Kingdee", "002371.SZ": "Naura Tech",
    "600900.SS": "CYPC Hydro", "000333.SZ": "Midea Group",
    "300124.SZ": "Inovance Tech", "002594.SZ": "BYD",
}


async def main():
    CAPITAL = 1_000_000

    print("\n" + "="*110)
    print("  FinClaw -- MASTER STRATEGIES (5-Year Backtest)")
    print("  Buffett | Dalio | Druckenmiller | Soros | Lynch")
    print("="*110)

    # Phase 1: Scan all
    print(f"\n  Scanning {len(ALL_STOCKS)} stocks...")
    selector = AssetSelector()
    all_data = []

    for ticker, name in ALL_STOCKS.items():
        h = fetch(ticker, "5y")
        if not h: continue

        bh = h[-1]["price"]/h[0]["price"]-1
        years = max(len(h)/252, 0.5)

        bt = BacktesterV7(initial_capital=CAPITAL//5)
        r = await bt.run(ticker, "v7", h)

        prices = [x["price"] for x in h]
        rets = [prices[i]/prices[i-1]-1 for i in range(1, len(prices))]
        ann_vol = (sum((rv-sum(rets)/len(rets))**2 for rv in rets)/(len(rets)-1))**0.5*math.sqrt(252) if len(rets)>1 else 0.3

        # Drawdown from peak
        peak = prices[0]; max_dd_from_peak = 0
        for p in prices:
            peak = max(peak, p)
            dd = (p - peak) / peak
            max_dd_from_peak = min(max_dd_from_peak, dd)

        # Earnings proxy: 1Y momentum (recent growth)
        recent_1y = prices[-1]/prices[max(0, len(prices)-252)]-1 if len(prices) > 252 else bh/max(years,1)

        # 3Y CAGR
        if len(prices) > 756:
            cagr_3y = (prices[-1]/prices[-756])**(1/3)-1
        else:
            cagr_3y = (1+bh)**(1/years)-1 if bh > -1 else 0

        try:
            score = selector.score_asset(
                [x["price"] for x in h[:min(150,len(h))]],
                [x.get("volume",0) for x in h[:min(150,len(h))]]
            )
            grade = score.grade; composite = score.composite
        except:
            grade = AssetGrade.C; composite = 0

        all_data.append({
            "ticker": ticker, "name": name, "h": h, "prices": prices,
            "bh": bh, "wt_ret": r.total_return,
            "wt_ann": (1+r.total_return)**(1/years)-1 if r.total_return>-1 else -1,
            "wt_dd": r.max_drawdown, "years": years,
            "grade": grade, "composite": composite,
            "ann_vol": ann_vol, "max_dd_peak": max_dd_from_peak,
            "recent_1y": recent_1y, "cagr_3y": cagr_3y,
        })

        print(f"    {ticker:<12} {name:<18} WT={r.total_return:>+7.1%}({(1+r.total_return)**(1/years)-1 if r.total_return>-1 else -1:>+5.1%}/y) vol={ann_vol:.0%}")

    N = len(all_data)
    print(f"\n  {N} stocks scanned.\n")

    # ═══ STRATEGY SELECTION ═══

    # 1. BUFFETT: Quality + Value (low vol, high compound, buy on dips)
    # Score: high CAGR + low vol + large drawdown recovery (bought during fear)
    for d in all_data:
        # Buffett loves companies that recovered from big dips
        recovery_bonus = max(-d["max_dd_peak"] - 0.20, 0) * 2  # bonus for >20% drawdown recovery
        d["buffett_score"] = d["cagr_3y"] * 0.4 + (1-min(d["ann_vol"],1)) * 0.3 + recovery_bonus * 0.3
    buffett_pool = sorted(all_data, key=lambda x: x["buffett_score"], reverse=True)[:8]

    # 2. DALIO: Low correlation + risk parity
    # Start with top-15 by composite, then filter for low correlation
    by_comp = sorted(all_data, key=lambda x: x["composite"], reverse=True)
    dalio_pool = [by_comp[0]]
    for candidate in by_comp[1:]:
        # Check correlation with existing pool members
        max_corr = max(
            _corr(candidate["prices"], existing["prices"])
            for existing in dalio_pool
        )
        if max_corr < 0.60:  # only add if low correlation
            dalio_pool.append(candidate)
        if len(dalio_pool) >= 10:
            break
    # Risk parity: weight inversely proportional to volatility
    for d in dalio_pool:
        d["risk_parity_w"] = 1.0 / max(d["ann_vol"], 0.10)
    total_rp = sum(d["risk_parity_w"] for d in dalio_pool)
    for d in dalio_pool: d["alloc"] = d["risk_parity_w"] / total_rp

    # 3. DRUCKENMILLER: Pure momentum, extreme concentration
    # Top-3 by recent 1Y momentum
    drucken_pool = sorted(all_data, key=lambda x: x["recent_1y"], reverse=True)[:3]
    for d in drucken_pool: d["alloc"] = 1.0/3

    # 4. SOROS: Narrative + momentum (AI theme stocks with strongest trend)
    ai_narrative = [d for d in all_data if any(kw in d["name"].lower() for kw in
                    ["nvidia","broadcom","arista","cambricon","smic","amd","palantir",
                     "meta","alphabet","naura","shuguang","catl","byd"])]
    if len(ai_narrative) < 3:
        ai_narrative = sorted(all_data, key=lambda x: x["recent_1y"], reverse=True)[:5]
    soros_pool = sorted(ai_narrative, key=lambda x: x["wt_ann"], reverse=True)[:5]
    for d in soros_pool: d["alloc"] = 1.0/len(soros_pool)

    # 5. LYNCH: High growth + reasonable vol (tenbagger candidates)
    for d in all_data:
        growth_rate = max(d["cagr_3y"], 0)
        d["lynch_score"] = growth_rate / max(d["ann_vol"], 0.10)  # PEG-like ratio
    lynch_pool = sorted(all_data, key=lambda x: x["lynch_score"], reverse=True)[:6]
    for d in lynch_pool: d["alloc"] = 1.0/len(lynch_pool)

    # Buffett: equal weight
    for d in buffett_pool: d["alloc"] = 1.0/len(buffett_pool)

    strategies = [
        ("DRUCKENMILLER Momentum", drucken_pool, "Top-3 strongest 1Y momentum, equal weight"),
        ("SOROS Reflexivity", soros_pool, "AI narrative + momentum, top-5"),
        ("LYNCH Tenbagger", lynch_pool, "High growth/vol ratio, top-6"),
        ("BUFFETT Value", buffett_pool, "Quality + dip recovery, top-8"),
        ("DALIO All-Weather", dalio_pool, "Low correlation, risk parity weighted"),
    ]

    print("="*110)
    print("  MASTER STRATEGY RESULTS (5 Years)")
    print("="*110)

    summary = []

    for strat_name, pool, desc in strategies:
        total_pnl = 0
        avg_years = sum(d["years"] for d in pool) / len(pool)
        worst_dd = 0
        holdings = []

        for d in pool:
            cap = CAPITAL * d["alloc"]
            bt = BacktesterV7(initial_capital=cap)
            r = await bt.run(d["ticker"], "v7", d["h"])
            pnl = cap * r.total_return
            total_pnl += pnl
            worst_dd = min(worst_dd, r.max_drawdown)
            holdings.append(f"{d['name']}({r.total_return:+.0%})")

        port_ret = total_pnl / CAPITAL
        ann_ret = (1 + port_ret) ** (1 / avg_years) - 1 if port_ret > -1 else -1
        final = CAPITAL + total_pnl

        summary.append((strat_name, port_ret, ann_ret, worst_dd, final, total_pnl, holdings, desc))

    # Sort by annual return
    summary.sort(key=lambda x: x[2], reverse=True)

    print(f"\n  {'#':<3} {'Strategy':<28} {'5Y Return':>10} {'Annual':>8} {'MaxDD':>7} {'100W->':>10} {'P&L':>12}")
    print("  " + "-"*90)

    for i, (name, ret, ann, dd, final, pnl, holdings, desc) in enumerate(summary, 1):
        print(f"  {i:<3} {name:<28} {ret:>+9.1%} {ann:>+7.1%}/y {dd:>+6.1%} {final:>9,.0f} {pnl:>+11,.0f}")
        print(f"      {desc}")
        print(f"      Holdings: {', '.join(holdings)}")
        print()

    # Risk-return scatter
    print(f"\n  RISK vs RETURN:")
    print(f"  {'Strategy':<28} {'Annual':>8} {'MaxDD':>7} {'Return/Risk':>12} {'Verdict':>12}")
    print("  " + "-"*72)
    for name, ret, ann, dd, final, pnl, holdings, desc in summary:
        rr = ann / max(abs(dd), 0.01)
        verdict = "BEST R/R" if rr > 0.5 else ("GOOD" if rr > 0.3 else "RISKY")
        print(f"  {name:<28} {ann:>+7.1%}/y {dd:>+6.1%} {rr:>11.2f} {verdict:>12}")

    print("="*110)


if __name__ == "__main__":
    asyncio.run(main())
