"""
FinClaw — Real Historical Data Benchmark
=============================================
Uses yfinance to get REAL stock data and validate our engine
on actual market conditions (not simulations).

This is the ULTIMATE test — no synthetic data, no seed tricks.
"""
import asyncio
import sys, os
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.backtester_v7 import BacktesterV7
from agents.ahf_simulator import AHFBacktester

try:
    import yfinance as yf
except ImportError:
    print("pip install yfinance")
    sys.exit(1)


def fetch_real_data(ticker, period="1y"):
    """Fetch real historical data from Yahoo Finance."""
    stock = yf.Ticker(ticker)
    df = stock.history(period=period)
    if df.empty:
        return None
    hist = []
    for idx, row in df.iterrows():
        hist.append({
            "date": idx.to_pydatetime(),
            "price": float(row["Close"]),
            "volume": float(row["Volume"]),
        })
    return hist


async def main():
    print("\n" + "="*100)
    print("  FinClaw v7 -- REAL DATA BENCHMARK")
    print("  (Yahoo Finance historical data, no simulations)")
    print("="*100 + "\n")

    # Real tickers — diverse market conditions
    tickers = {
        "NVDA":  "AI Bull (2024-2025)",
        "AAPL":  "Mega Cap Stable",
        "TSLA":  "High Volatility",
        "META":  "Recovery Play",
        "MSFT":  "Steady Grower",
        "AMZN":  "Cloud/Retail",
        "INTC":  "Turnaround/Bear",
        "GOOG":  "Search + AI",
        "AMD":   "Semiconductor Cycle",
        "COIN":  "Crypto Proxy",
    }

    print(f"  Fetching {len(tickers)} real tickers from Yahoo Finance...\n")

    results = []
    ahf_bt = AHFBacktester(initial_capital=10000)

    header = f"  {'Ticker':<8} {'Description':<22} {'B&H':>7} | {'WT v7':>7} {'alpha':>7} | {'AHF':>7} {'alpha':>7} | {'Winner':>8}"
    print(header)
    print("  " + "-"*95)

    wt_wins_ahf = 0
    total = 0

    for ticker, desc in tickers.items():
        try:
            h = fetch_real_data(ticker, "1y")
            if not h or len(h) < 60:
                print(f"  {ticker:<8} SKIP (insufficient data)")
                continue

            bh = h[-1]["price"] / h[0]["price"] - 1

            # FinClaw v7
            bt = BacktesterV7(initial_capital=10000)
            r = await bt.run(ticker, "v7", h)
            wt_alpha = r.total_return - bh

            # AHF (realistic)
            ahf_r = ahf_bt.run(h)
            ahf_alpha = ahf_r["alpha"]

            beat_ahf = wt_alpha > ahf_alpha
            if beat_ahf: wt_wins_ahf += 1
            total += 1

            winner = "WT" if beat_ahf else "AHF"
            results.append({
                "ticker": ticker, "desc": desc, "bh": bh,
                "wt_ret": r.total_return, "wt_alpha": wt_alpha,
                "wt_dd": r.max_drawdown, "wt_trades": r.total_trades,
                "ahf_ret": ahf_r["total_return"], "ahf_alpha": ahf_alpha,
            })

            print(f"  {ticker:<8} {desc:<22} {bh:>+6.1%} | {r.total_return:>+6.1%} {wt_alpha:>+6.1%} | "
                  f"{ahf_r['total_return']:>+6.1%} {ahf_alpha:>+6.1%} | {winner:>8}")

        except Exception as e:
            print(f"  {ticker:<8} ERROR: {e}")

    if not results:
        print("\n  No results. Check internet connection.")
        return

    # Summary
    avg_wt_alpha = sum(r["wt_alpha"] for r in results) / len(results)
    avg_ahf_alpha = sum(r["ahf_alpha"] for r in results) / len(results)
    avg_wt_dd = sum(r["wt_dd"] for r in results) / len(results)

    print(f"\n" + "="*100)
    print(f"  REAL DATA RESULTS")
    print("="*100)
    print(f"\n  {'Metric':<30} {'FinClaw':>12} {'AHF':>12}")
    print("  " + "-"*60)
    print(f"  {'Avg Alpha':<30} {avg_wt_alpha:>+11.2%} {avg_ahf_alpha:>+11.2%}")
    print(f"  {'Avg MaxDD':<30} {avg_wt_dd:>+11.2%}          —")
    print(f"  {'Win Rate vs opponent':<30} {wt_wins_ahf}/{total}          {total-wt_wins_ahf}/{total}")
    print(f"\n  Gap: FinClaw {avg_wt_alpha-avg_ahf_alpha:+.2%} vs AHF")

    if avg_wt_alpha > avg_ahf_alpha:
        print(f"\n  >>> FinClaw WINS on real data! <<<")
    print("="*100)

if __name__ == "__main__":
    asyncio.run(main())
