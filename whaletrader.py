#!/usr/bin/env python3
"""
WhaleTrader CLI — One-command trading system
=============================================
Usage:
  python whaletrader.py scan --market us --style aggressive
  python whaletrader.py scan --market china --style buffett --capital 1000000
  python whaletrader.py scan --market all --style soros --report
  python whaletrader.py backtest --ticker NVDA --period 5y
  python whaletrader.py test
  python whaletrader.py info

Styles:
  druckenmiller  — Top-3 momentum, max conviction (年化20-35%)
  soros          — AI/narrative + momentum, top-5 (年化25-30%)
  lynch          — Growth/vol ratio, top-6 (年化20-27%)
  buffett        — Quality + dip recovery, top-8 (年化20-30%)
  dalio          — All-weather, low correlation, risk parity (年化15-20%)
  aggressive     — Top-5 by return (年化25-35%)
  balanced       — Top-10 grade-weighted (年化10-15%)
  conservative   — Top-15 low-vol (年化8-12%)
"""
import asyncio, argparse, math, sys, os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.backtester_v7 import BacktesterV7
from agents.signal_engine_v9 import AssetSelector, AssetGrade

try:
    import yfinance as yf
except ImportError:
    print("ERROR: pip install yfinance"); sys.exit(1)


# ═══ PRESET STOCK UNIVERSES ═══
UNIVERSES = {
    "us": {
        "NVDA": "NVIDIA", "AVGO": "Broadcom", "ANET": "Arista",
        "NFLX": "Netflix", "LLY": "Eli Lilly", "PLTR": "Palantir",
        "META": "Meta", "GOOG": "Alphabet", "AMD": "AMD",
        "AAPL": "Apple", "MSFT": "Microsoft", "AMZN": "Amazon",
        "TSLA": "Tesla", "COST": "Costco", "WMT": "Walmart",
        "XOM": "ExxonMobil", "CVX": "Chevron", "ABBV": "AbbVie",
        "JPM": "JPMorgan", "V": "Visa", "CAT": "Caterpillar",
        "KO": "Coca-Cola", "PG": "P&G", "ISRG": "Intuitive Surg",
        "CRWD": "CrowdStrike", "PANW": "Palo Alto", "UBER": "Uber",
    },
    "china": {
        "688256.SS": "Cambricon", "601899.SS": "Zijin Mining",
        "601600.SS": "Aluminum Corp", "603019.SS": "Zhongke Shuguang",
        "300750.SZ": "CATL", "300274.SZ": "Sungrow Power",
        "002812.SZ": "Yunnan Energy", "603993.SS": "Luoyang Moly",
        "600547.SS": "Shandong Gold", "601985.SS": "CRPC Nuclear",
        "300474.SZ": "Kingdee", "002371.SZ": "Naura Tech",
        "600900.SS": "CYPC Hydro", "000333.SZ": "Midea Group",
        "300124.SZ": "Inovance Tech", "002594.SZ": "BYD",
        "600519.SS": "Moutai", "000858.SZ": "Wuliangye",
        "601318.SS": "Ping An", "600036.SS": "CMB",
    },
    "hk": {
        "0700.HK": "Tencent", "9988.HK": "Alibaba",
        "3690.HK": "Meituan", "1211.HK": "BYD HK",
        "9618.HK": "JD.com", "1810.HK": "Xiaomi",
        "2318.HK": "Ping An HK", "0941.HK": "China Mobile",
    },
}


# ═══ STRATEGY PRESETS ═══
STRATEGIES = {
    "druckenmiller": {
        "desc": "Top-3 momentum, max conviction",
        "risk": "VERY HIGH", "target_ann": "20-35%",
        "select": lambda data: sorted(data, key=lambda x: x.get("recent_1y",0), reverse=True)[:3],
        "alloc": "equal",
    },
    "soros": {
        "desc": "AI narrative + momentum, top-5",
        "risk": "HIGH", "target_ann": "25-30%",
        "select": lambda data: sorted(
            [d for d in data if d.get("wt_ann",0) > 0.10],
            key=lambda x: x.get("wt_ann",0), reverse=True
        )[:5] or sorted(data, key=lambda x: x.get("wt_ann",0), reverse=True)[:5],
        "alloc": "equal",
    },
    "lynch": {
        "desc": "High growth/vol ratio, top-6",
        "risk": "HIGH", "target_ann": "20-27%",
        "select": lambda data: sorted(data,
            key=lambda x: max(x.get("cagr_3y",0),0)/max(x.get("ann_vol",0.1),0.1),
            reverse=True)[:6],
        "alloc": "equal",
    },
    "buffett": {
        "desc": "Quality + dip recovery, top-8",
        "risk": "MEDIUM-HIGH", "target_ann": "20-30%",
        "select": lambda data: sorted(data,
            key=lambda x: x.get("cagr_3y",0)*0.4 + (1-min(x.get("ann_vol",0.3),1))*0.3 + max(-x.get("max_dd_peak",0)-0.2,0)*0.6,
            reverse=True)[:8],
        "alloc": "equal",
    },
    "dalio": {
        "desc": "All-weather, low corr, risk parity",
        "risk": "MEDIUM", "target_ann": "15-20%",
        "select": lambda data: sorted(data, key=lambda x: x.get("composite",0), reverse=True)[:12],
        "alloc": "risk_parity",
    },
    "aggressive": {
        "desc": "Top-5 by WT return",
        "risk": "HIGH", "target_ann": "25-35%",
        "select": lambda data: sorted(data, key=lambda x: x.get("wt_ann",0), reverse=True)[:5],
        "alloc": "equal",
    },
    "balanced": {
        "desc": "Top-10 grade-weighted",
        "risk": "MEDIUM", "target_ann": "10-15%",
        "select": lambda data: sorted(data, key=lambda x: x.get("composite",0), reverse=True)[:10],
        "alloc": "grade",
    },
    "conservative": {
        "desc": "Top-15 low-vol, safe",
        "risk": "LOW", "target_ann": "8-12%",
        "select": lambda data: sorted(data,
            key=lambda x: x.get("composite",0)*0.3+(1-min(x.get("ann_vol",0.3),1))*0.7,
            reverse=True)[:15],
        "alloc": "equal",
    },
}


def fetch_data(ticker, period="5y"):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        if df.empty or len(df) < 60: return None
        return [{"date": idx.to_pydatetime(), "price": float(row["Close"]),
                 "volume": float(row["Volume"])} for idx, row in df.iterrows()]
    except:
        return None


async def scan_universe(tickers, period="5y", capital=1000000):
    """Scan and grade all stocks in a universe."""
    selector = AssetSelector()
    all_data = []

    for ticker, name in tickers.items():
        h = fetch_data(ticker, period)
        if not h: continue

        bh = h[-1]["price"]/h[0]["price"]-1
        years = max(len(h)/252, 0.5)

        bt = BacktesterV7(initial_capital=capital//10)
        r = await bt.run(ticker, "v7", h)

        prices = [x["price"] for x in h]
        rets = [prices[i]/prices[i-1]-1 for i in range(1, len(prices))]
        ann_vol = (sum((rv-sum(rets)/len(rets))**2 for rv in rets)/(len(rets)-1))**0.5*math.sqrt(252) if len(rets)>1 else 0.3

        peak = prices[0]; max_dd = 0
        for p in prices:
            peak = max(peak, p)
            max_dd = min(max_dd, (p-peak)/peak)

        recent_1y = prices[-1]/prices[max(0,len(prices)-252)]-1 if len(prices)>252 else bh/max(years,1)
        cagr_3y = (prices[-1]/prices[max(0,len(prices)-756)])**(1/min(3,years))-1 if len(prices)>100 else 0

        try:
            score = selector.score_asset(
                [x["price"] for x in h[:min(150,len(h))]],
                [x.get("volume",0) for x in h[:min(150,len(h))]])
            grade = score.grade; composite = score.composite
        except:
            grade = AssetGrade.C; composite = 0

        all_data.append({
            "ticker": ticker, "name": name, "h": h,
            "bh": bh, "wt_ret": r.total_return,
            "wt_ann": (1+r.total_return)**(1/years)-1 if r.total_return>-1 else -1,
            "wt_dd": r.max_drawdown, "years": years,
            "grade": grade, "composite": composite,
            "ann_vol": ann_vol, "max_dd_peak": max_dd,
            "recent_1y": recent_1y, "cagr_3y": cagr_3y,
        })

    return all_data


async def run_strategy(style, data, capital):
    """Run a preset strategy and return results."""
    strat = STRATEGIES[style]
    pool = strat["select"](data)
    if not pool:
        return None

    GRADE_W = {AssetGrade.A_PLUS: 12, AssetGrade.A: 6, AssetGrade.B: 2,
               AssetGrade.C: 0.5, AssetGrade.F: 0.1}

    if strat["alloc"] == "grade":
        total_w = sum(GRADE_W.get(d["grade"], 1) for d in pool)
        for d in pool: d["alloc"] = GRADE_W.get(d["grade"], 1) / total_w
    elif strat["alloc"] == "risk_parity":
        for d in pool: d["rp_w"] = 1.0 / max(d["ann_vol"], 0.10)
        total_rp = sum(d["rp_w"] for d in pool)
        for d in pool: d["alloc"] = d["rp_w"] / total_rp
    else:
        for d in pool: d["alloc"] = 1.0 / len(pool)

    total_pnl = 0
    avg_years = sum(d["years"] for d in pool) / len(pool)
    results_detail = []

    for d in pool:
        cap = capital * d["alloc"]
        bt = BacktesterV7(initial_capital=cap)
        r = await bt.run(d["ticker"], "v7", d["h"])
        pnl = cap * r.total_return
        total_pnl += pnl
        results_detail.append({
            "ticker": d["ticker"], "name": d["name"],
            "alloc": d["alloc"], "capital": cap,
            "wt_ret": r.total_return, "pnl": pnl,
            "dd": r.max_drawdown, "grade": d["grade"].value,
        })

    port_ret = total_pnl / capital
    ann_ret = (1 + port_ret) ** (1 / avg_years) - 1 if port_ret > -1 else -1

    return {
        "style": style, "desc": strat["desc"], "risk": strat["risk"],
        "total_ret": port_ret, "ann_ret": ann_ret, "pnl": total_pnl,
        "years": avg_years, "holdings": results_detail,
    }


async def cmd_scan(args):
    """Scan a market with a strategy."""
    capital = args.capital
    period = args.period
    style = args.style
    markets = [args.market] if args.market != "all" else ["us", "china", "hk"]

    print(f"\n  WhaleTrader Scan")
    print(f"  Market: {args.market} | Style: {style} | Capital: {capital:,.0f} | Period: {period}")
    print(f"  Strategy: {STRATEGIES[style]['desc']}")
    print(f"  Risk Level: {STRATEGIES[style]['risk']}")
    print(f"  Target Annual: {STRATEGIES[style]['target_ann']}")
    print("="*80)

    for market in markets:
        if market not in UNIVERSES:
            print(f"  Unknown market: {market}"); continue

        print(f"\n  Scanning {market.upper()} ({len(UNIVERSES[market])} stocks)...")
        data = await scan_universe(UNIVERSES[market], period, capital)
        result = await run_strategy(style, data, capital)

        if not result:
            print("  No stocks matched criteria."); continue

        print(f"\n  === {market.upper()} — {style.upper()} ===")
        print(f"\n  {'Ticker':<12} {'Name':<18} {'Grade':>5} {'Alloc':>6} {'Return':>8} {'P&L':>12}")
        print("  " + "-"*70)

        for h in result["holdings"]:
            print(f"  {h['ticker']:<12} {h['name']:<18} {h['grade']:>5} {h['alloc']:>5.0%} "
                  f"{h['wt_ret']:>+7.1%} {h['pnl']:>+11,.0f}")

        print(f"\n  Portfolio: {result['total_ret']:>+.1%} ({result['ann_ret']:>+.1%}/year)")
        print(f"  P&L: {result['pnl']:>+,.0f} | Final: {capital+result['pnl']:>,.0f}")

    print("="*80)


async def cmd_backtest(args):
    """Backtest a single ticker."""
    ticker = args.ticker
    period = args.period
    capital = args.capital

    print(f"\n  WhaleTrader Single Backtest: {ticker}")
    h = fetch_data(ticker, period)
    if not h:
        print(f"  ERROR: No data for {ticker}"); return

    bh = h[-1]["price"]/h[0]["price"]-1
    years = len(h)/252

    bt = BacktesterV7(initial_capital=capital)
    r = await bt.run(ticker, "v7", h)
    ann = (1+r.total_return)**(1/years)-1 if r.total_return>-1 else -1

    print(f"  Period: {years:.1f} years | B&H: {bh:+.1%}")
    print(f"  WT Return: {r.total_return:+.1%} ({ann:+.1%}/year)")
    print(f"  Alpha: {r.total_return-bh:+.1%}")
    print(f"  MaxDD: {r.max_drawdown:+.1%}")
    print(f"  Trades: {r.total_trades} | Win Rate: {r.win_rate:.0%}")
    print(f"  P&L: {capital*r.total_return:+,.0f} | Final: {capital*(1+r.total_return):,.0f}")


def cmd_info(args):
    """Show available strategies and markets."""
    print("\n  WhaleTrader — Available Strategies\n")
    print(f"  {'Style':<18} {'Risk':<15} {'Target':>12} {'Description'}")
    print("  " + "-"*75)
    for name, s in STRATEGIES.items():
        print(f"  {name:<18} {s['risk']:<15} {s['target_ann']:>12} {s['desc']}")

    print(f"\n  Available Markets: us, china, hk, all")
    print(f"  Default Period: 5y (options: 1y, 2y, 5y, 10y)")


def main():
    parser = argparse.ArgumentParser(description="WhaleTrader AI Trading Engine")
    sub = parser.add_subparsers(dest="command")

    # scan
    p_scan = sub.add_parser("scan", help="Scan market with strategy")
    p_scan.add_argument("--market", "-m", default="us", choices=["us","china","hk","all"])
    p_scan.add_argument("--style", "-s", default="soros", choices=list(STRATEGIES.keys()))
    p_scan.add_argument("--capital", "-c", type=float, default=1000000)
    p_scan.add_argument("--period", "-p", default="5y")
    p_scan.add_argument("--report", "-r", action="store_true")

    # backtest
    p_bt = sub.add_parser("backtest", help="Backtest single ticker")
    p_bt.add_argument("--ticker", "-t", required=True)
    p_bt.add_argument("--period", "-p", default="5y")
    p_bt.add_argument("--capital", "-c", type=float, default=100000)

    # test
    sub.add_parser("test", help="Run test suite")

    # info
    sub.add_parser("info", help="Show strategies and markets")

    args = parser.parse_args()

    if args.command == "scan":
        asyncio.run(cmd_scan(args))
    elif args.command == "backtest":
        asyncio.run(cmd_backtest(args))
    elif args.command == "test":
        import subprocess
        r1 = subprocess.run([sys.executable, "tests/test_engine.py"], cwd=os.path.dirname(__file__))
        r2 = subprocess.run([sys.executable, "tests/test_picker.py"], cwd=os.path.dirname(__file__))
        exit(r1.returncode or r2.returncode)
    elif args.command == "info":
        cmd_info(args)
    else:
        parser.print_help()
        print("\n  Quick start:")
        print("    python whaletrader.py info")
        print("    python whaletrader.py scan --market us --style soros")
        print("    python whaletrader.py backtest --ticker NVDA")


if __name__ == "__main__":
    main()
