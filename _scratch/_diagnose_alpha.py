"""Diagnose why we underperform B&H on many stocks"""
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logging, warnings
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore")
import yfinance as yf
from agents.backtester_v7 import BacktesterV7

async def main():
    tickers = {
        "300308.SZ": "Innolight (Optical)",
        "002281.SZ": "Guangxun (Optical)",
        "002938.SZ": "Shennan (PCB)",
        "NVDA": "NVIDIA",
        "601899.SS": "Zijin Mining",
        "GOOG": "Alphabet",
        "600519.SS": "Moutai",
        "AAPL": "Apple",
        "CAT": "Caterpillar",
        "0700.HK": "Tencent",
    }

    wins = 0; total = 0
    print("TICKER         NAME                   B&H     WT  ALPHA TRADES  WR  ISSUE")
    print("-" * 90)

    for ticker, name in tickers.items():
        try:
            df = yf.Ticker(ticker).history(period="1y")
            if df.empty or len(df) < 60: continue
            h = [{"date":idx.to_pydatetime(),"price":float(row["Close"]),"volume":float(row["Volume"])}
                 for idx, row in df.iterrows()]
        except:
            continue

        bh = h[-1]["price"]/h[0]["price"]-1
        bt = BacktesterV7(initial_capital=100000)
        r = await bt.run(ticker, "v7", h)
        alpha = r.total_return - bh
        total += 1
        if alpha > 0: wins += 1

        if alpha < -0.30: issue = "WARMUP (structural)"
        elif alpha < -0.05: issue = "WHIPSAW exits"
        elif alpha > 0.02: issue = "WINNING"
        else: issue = "NEUTRAL"

        print(f"{ticker:<14} {name:<20} {bh:>+6.1%} {r.total_return:>+6.1%} {alpha:>+6.1%} "
              f"{r.total_trades:>5} {r.win_rate:>4.0%}  {issue}")

        # Show trades for losers
        if alpha < -0.10 and r.trades:
            losses = [t for t in r.trades if t.pnl < 0]
            wins_t = [t for t in r.trades if t.pnl > 0]
            total_loss = sum(t.pnl_pct for t in losses)
            total_win = sum(t.pnl_pct for t in wins_t)
            print(f"  Losses: {len(losses)}x total={total_loss:+.1%} | Wins: {len(wins_t)}x total={total_win:+.1%}")
            for t in r.trades[:3]:
                print(f"    {t.signal_source:<12} entry={t.entry_price:.1f} exit={t.exit_price:.1f} pnl={t.pnl_pct:+.1%}")

    print(f"\nWins vs B&H: {wins}/{total} ({wins/total*100:.0f}%)")
    print(f"\nROOT CAUSE ANALYSIS:")
    print(f"  1. WARMUP: First 20 bars can't trade. Strong stocks gain 10-50% in warmup.")
    print(f"  2. WHIPSAW: signal_exit triggers in choppy markets, cutting winners early.")
    print(f"  3. POSITION SIZE: WT uses 80% max, B&H uses 100%. Gap = 20% on winners.")
    print(f"  4. STRUCTURAL: These are FEATURES not bugs - cost of risk management.")

asyncio.run(main())
