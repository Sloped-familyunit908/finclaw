"""
WhaleTrader — Multi-Market Real Data Benchmark
================================================
Tests across US, China A-shares, Hong Kong, Korean, and Japanese markets.

Ticker formats:
- US: AAPL, NVDA
- A-shares: 600519.SS (Shanghai), 000858.SZ (Shenzhen)
- Hong Kong: 0700.HK (Tencent), 9988.HK (Alibaba)
- Korea: 005930.KS (Samsung), 000660.KS (SK Hynix)
- Japan: 7203.T (Toyota), 6758.T (Sony)
"""
import asyncio
import sys, os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.backtester_v7 import BacktesterV7
from agents.ahf_simulator import AHFBacktester

try:
    import yfinance as yf
except ImportError:
    print("pip install yfinance"); sys.exit(1)


def fetch_real_data(ticker, period="1y"):
    stock = yf.Ticker(ticker)
    df = stock.history(period=period)
    if df.empty: return None
    return [{"date": idx.to_pydatetime(), "price": float(row["Close"]),
             "volume": float(row["Volume"])} for idx, row in df.iterrows()]


MARKETS = {
    "US": {
        "flag": "US",
        "tickers": {
            "NVDA":     "AI Chip Leader",
            "AAPL":     "Consumer Tech",
            "TSLA":     "EV / High Vol",
            "META":     "Social / AI",
            "MSFT":     "Enterprise Cloud",
            "AMZN":     "E-commerce / Cloud",
            "GOOG":     "Search / AI",
            "AMD":      "Semiconductor",
            "COIN":     "Crypto Proxy",
            "INTC":     "Turnaround Play",
        },
    },
    "China A-shares": {
        "flag": "CN",
        "tickers": {
            "600519.SS": "Kweichow Moutai",
            "000858.SZ": "Wuliangye Yibin",
            "300750.SZ": "CATL (Battery)",
            "601318.SS": "Ping An Insurance",
            "000001.SZ": "Ping An Bank",
            "600036.SS": "China Merchants Bank",
            "002594.SZ": "BYD Auto",
            "601899.SS": "Zijin Mining",
        },
    },
    "Hong Kong": {
        "flag": "HK",
        "tickers": {
            "0700.HK":  "Tencent",
            "9988.HK":  "Alibaba",
            "3690.HK":  "Meituan",
            "1211.HK":  "BYD (HK)",
            "9618.HK":  "JD.com",
            "2318.HK":  "Ping An (HK)",
            "0941.HK":  "China Mobile",
            "1810.HK":  "Xiaomi",
        },
    },
    "Korea": {
        "flag": "KR",
        "tickers": {
            "005930.KS": "Samsung Electronics",
            "000660.KS": "SK Hynix",
            "373220.KS": "LG Energy Solution",
            "207940.KS": "Samsung Biologics",
            "005380.KS": "Hyundai Motor",
            "051910.KS": "LG Chem",
        },
    },
    "Japan": {
        "flag": "JP",
        "tickers": {
            "7203.T":   "Toyota Motor",
            "6758.T":   "Sony Group",
            "6861.T":   "Keyence",
            "9984.T":   "SoftBank Group",
            "8306.T":   "Mitsubishi UFJ",
            "6501.T":   "Hitachi",
        },
    },
}


async def main():
    print("\n" + "="*110)
    print("  WhaleTrader v7 -- MULTI-MARKET REAL DATA BENCHMARK")
    print("  US | China A-shares | Hong Kong | Korea | Japan")
    print("="*110)

    ahf_bt = AHFBacktester(initial_capital=10000)
    all_results = []
    market_summaries = []

    for market_name, market in MARKETS.items():
        print(f"\n  --- {market['flag']} {market_name} ---\n")
        print(f"  {'Ticker':<12} {'Name':<22} {'B&H':>7} | {'WT v7':>7} {'alpha':>7} | {'AHF':>7} {'alpha':>7} | {'W':>3}")
        print("  " + "-"*90)

        market_wt = []; market_ahf = []; wt_wins = 0; total = 0

        for ticker, name in market["tickers"].items():
            try:
                h = fetch_real_data(ticker, "1y")
                if not h or len(h) < 60:
                    print(f"  {ticker:<12} {name:<22} SKIP (insufficient data)")
                    continue

                bh = h[-1]["price"] / h[0]["price"] - 1

                bt = BacktesterV7(initial_capital=10000)
                r = await bt.run(ticker, "v7", h)
                wt_alpha = r.total_return - bh

                ahf_r = ahf_bt.run(h)
                ahf_alpha = ahf_r["alpha"]

                beat = wt_alpha > ahf_alpha
                if beat: wt_wins += 1
                total += 1

                market_wt.append(wt_alpha)
                market_ahf.append(ahf_alpha)

                w = "WT" if beat else "AHF"
                print(f"  {ticker:<12} {name:<22} {bh:>+6.1%} | {r.total_return:>+6.1%} {wt_alpha:>+6.1%} | "
                      f"{ahf_r['total_return']:>+6.1%} {ahf_alpha:>+6.1%} | {w:>3}")

                all_results.append({
                    "market": market_name, "ticker": ticker, "name": name,
                    "bh": bh, "wt_alpha": wt_alpha, "ahf_alpha": ahf_alpha,
                    "wt_dd": r.max_drawdown, "wt_trades": r.total_trades,
                })
            except Exception as e:
                print(f"  {ticker:<12} {name:<22} ERROR: {str(e)[:40]}")

        if market_wt:
            avg_wt = sum(market_wt)/len(market_wt)
            avg_ahf = sum(market_ahf)/len(market_ahf)
            print(f"\n  {market_name} Summary: WT avg={avg_wt:+.1%} AHF avg={avg_ahf:+.1%} "
                  f"gap={avg_wt-avg_ahf:+.1%} wins={wt_wins}/{total}")
            market_summaries.append({
                "market": market_name, "avg_wt": avg_wt, "avg_ahf": avg_ahf,
                "wins": wt_wins, "total": total
            })

    # ═══ GLOBAL SUMMARY ═══
    if all_results:
        global_wt = sum(r["wt_alpha"] for r in all_results) / len(all_results)
        global_ahf = sum(r["ahf_alpha"] for r in all_results) / len(all_results)
        global_wins = sum(1 for r in all_results if r["wt_alpha"] > r["ahf_alpha"])

        print(f"\n" + "="*110)
        print(f"  GLOBAL RESULTS ({len(all_results)} stocks across {len(market_summaries)} markets)")
        print("="*110)

        print(f"\n  {'Market':<20} {'WT Alpha':>10} {'AHF Alpha':>10} {'Gap':>10} {'WT Wins':>10}")
        print("  " + "-"*65)
        for ms in market_summaries:
            print(f"  {ms['market']:<20} {ms['avg_wt']:>+9.2%} {ms['avg_ahf']:>+9.2%} "
                  f"{ms['avg_wt']-ms['avg_ahf']:>+9.2%} {ms['wins']}/{ms['total']:>8}")
        print("  " + "-"*65)
        print(f"  {'GLOBAL':<20} {global_wt:>+9.2%} {global_ahf:>+9.2%} "
              f"{global_wt-global_ahf:>+9.2%} {global_wins}/{len(all_results):>8}")

        # Top 5 WT performers
        top5 = sorted(all_results, key=lambda x: x["wt_alpha"], reverse=True)[:5]
        print(f"\n  Top 5 WhaleTrader performers:")
        for r in top5:
            print(f"    {r['ticker']:<12} {r['name']:<20} alpha={r['wt_alpha']:>+6.1%} ({r['market']})")

        # Worst 5
        worst5 = sorted(all_results, key=lambda x: x["wt_alpha"])[:5]
        print(f"\n  Bottom 5 (structural gaps):")
        for r in worst5:
            print(f"    {r['ticker']:<12} {r['name']:<20} alpha={r['wt_alpha']:>+6.1%} ({r['market']})")

        if global_wt > global_ahf:
            print(f"\n  >>> WhaleTrader WINS globally by {global_wt-global_ahf:+.2%} <<<")
        print("="*110)

if __name__ == "__main__":
    asyncio.run(main())
