"""
WhaleTrader — Smart Picker Validation
=======================================
Does the multi-factor picker ACTUALLY select better stocks?
Test: scan 100+ stocks, pick top-10, compare vs random and vs old method.
"""
import asyncio, math, sys, os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.backtester_v7 import BacktesterV7
from agents.stock_picker import MultiFactorPicker, ConvictionLevel

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


ALL = {
    # US
    "NVDA":"NVIDIA","AVGO":"Broadcom","AMD":"AMD","ANET":"Arista","MU":"Micron",
    "AAPL":"Apple","MSFT":"Microsoft","GOOG":"Alphabet","AMZN":"Amazon","META":"Meta",
    "TSLA":"Tesla","NFLX":"Netflix","ORCL":"Oracle",
    "PLTR":"Palantir","COIN":"Coinbase","ROKU":"Roku","SHOP":"Shopify",
    "LLY":"Eli Lilly","UNH":"UnitedHealth","ABBV":"AbbVie","MRK":"Merck","ISRG":"Intuitive",
    "COST":"Costco","WMT":"Walmart","KO":"Coca-Cola","PG":"P&G",
    "XOM":"ExxonMobil","CVX":"Chevron","OXY":"Occidental",
    "JPM":"JPMorgan","GS":"Goldman","V":"Visa",
    "CAT":"Caterpillar","GE":"GE Aero","LMT":"Lockheed",
    "CRWD":"CrowdStrike","PANW":"Palo Alto","UBER":"Uber",
    # A-shares
    "688256.SS":"Cambricon","603019.SS":"Zhongke Shuguang","688012.SS":"SMIC",
    "002230.SZ":"iFLYTEK","002371.SZ":"Naura Tech","300474.SZ":"Kingdee",
    "300750.SZ":"CATL","002594.SZ":"BYD","300274.SZ":"Sungrow",
    "002812.SZ":"Yunnan Energy","601012.SS":"LONGi",
    "601899.SS":"Zijin Mining","603993.SS":"Luoyang Moly","600362.SS":"Jiangxi Cu",
    "600547.SS":"Shandong Gold","601600.SS":"Aluminum Corp",
    "600893.SS":"AVIC Shenyang","600519.SS":"Moutai","000858.SZ":"Wuliangye",
    "601318.SS":"Ping An","600036.SS":"CMB","601688.SS":"Huatai Sec",
    "300760.SZ":"Mindray","002415.SZ":"Hikvision","300059.SZ":"East Money",
    "000333.SZ":"Midea","601985.SS":"CRPC Nuclear","600900.SS":"CYPC Hydro",
    "300124.SZ":"Inovance","000651.SZ":"Gree",
}


async def main():
    CAPITAL = 1_000_000

    print("\n" + "="*110)
    print("  WhaleTrader — SMART PICKER VALIDATION")
    print("  Multi-Factor (Quant + Fundamental) Stock Selection")
    print("="*110)

    # Phase 1: Load data
    print(f"\n  Loading {len(ALL)} stocks...")
    stocks_data = []
    for ticker, name in ALL.items():
        h = fetch(ticker, "5y")
        if not h: continue
        stocks_data.append({"ticker": ticker, "name": name, "h": h})
    print(f"  {len(stocks_data)} stocks loaded.\n")

    # Phase 2: Multi-factor analysis (WITH fundamentals from yfinance)
    print("  Running multi-factor analysis (price + fundamentals)...\n")
    picker = MultiFactorPicker(use_fundamentals=True, use_llm=False)
    rankings = picker.rank_universe(stocks_data)

    # Show full rankings
    print(f"  {'#':<4} {'Conviction':<14} {'Ticker':<12} {'Name':<20} {'Score':>6} | Reasoning")
    print("  " + "-"*110)
    for i, a in enumerate(rankings, 1):
        cv = a.conviction.value
        tag = "***" if cv == "STRONG_BUY" else ("** " if cv == "BUY" else "   ")
        print(f"  {tag}{i:<3} {cv:<14} {a.ticker:<12} {a.name:<20} {a.score:>+5.3f} | {a.reasoning[:70]}")

    # Phase 3: Backtest top picks vs bottom picks
    print(f"\n" + "="*110)
    print("  BACKTEST: Top-5 vs Bottom-5 vs Random-5")
    print("="*110)

    top5 = rankings[:5]
    bottom5 = rankings[-5:]
    # Random middle
    mid = len(rankings)//2
    random5 = rankings[mid-2:mid+3]

    groups = [
        ("TOP-5 (Smart Picker)", top5),
        ("MIDDLE-5 (Random)", random5),
        ("BOTTOM-5 (Worst)", bottom5),
    ]

    for group_name, picks in groups:
        total_pnl = 0
        cap_each = CAPITAL / len(picks)
        avg_years = 0
        holdings = []

        for a in picks:
            h_data = next(d["h"] for d in stocks_data if d["ticker"] == a.ticker)
            bt = BacktesterV7(initial_capital=cap_each)
            r = await bt.run(a.ticker, "v7", h_data)
            pnl = cap_each * r.total_return
            total_pnl += pnl
            years = len(h_data) / 252
            avg_years += years
            holdings.append(f"{a.name}({r.total_return:+.0%})")

        avg_years /= len(picks)
        port_ret = total_pnl / CAPITAL
        ann = (1+port_ret)**(1/max(avg_years,0.5))-1 if port_ret>-1 else -1

        print(f"\n  {group_name}:")
        print(f"    Holdings: {', '.join(holdings)}")
        print(f"    5Y Return: {port_ret:+.1%} | Annual: {ann:+.1%}/y | P&L: {total_pnl:+,.0f}")

    # Phase 4: Different portfolio sizes
    print(f"\n" + "="*110)
    print("  PORTFOLIO SIZE ANALYSIS: Top-3 vs Top-5 vs Top-8 vs Top-10")
    print("="*110)

    for n_stocks in [3, 5, 8, 10, 15]:
        picks = rankings[:n_stocks]
        cap_each = CAPITAL / n_stocks
        total_pnl = 0; avg_years = 0

        for a in picks:
            h_data = next(d["h"] for d in stocks_data if d["ticker"] == a.ticker)
            bt = BacktesterV7(initial_capital=cap_each)
            r = await bt.run(a.ticker, "v7", h_data)
            total_pnl += cap_each * r.total_return
            avg_years += len(h_data) / 252

        avg_years /= n_stocks
        port_ret = total_pnl / CAPITAL
        ann = (1+port_ret)**(1/max(avg_years,0.5))-1 if port_ret>-1 else -1
        tickers = [a.ticker for a in picks]

        print(f"  Top-{n_stocks:>2}: {port_ret:>+7.1%} ({ann:>+6.1%}/y) | {', '.join(tickers[:5])}{'...' if n_stocks>5 else ''}")

    print("="*110)


if __name__ == "__main__":
    asyncio.run(main())
