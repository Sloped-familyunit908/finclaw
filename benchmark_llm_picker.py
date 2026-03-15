"""
WhaleTrader — LLM-Enhanced Picker vs Pure Quant Picker
=======================================================
Does AI disruption analysis actually improve stock selection?
"""
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.backtester_v7 import BacktesterV7
from agents.stock_picker import MultiFactorPicker
from agents.llm_analyzer import LLMStockAnalyzer

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

STOCKS = {
    "NVDA":"NVIDIA","AVGO":"Broadcom","AMD":"AMD","ANET":"Arista",
    "AAPL":"Apple","MSFT":"Microsoft","GOOG":"Alphabet","AMZN":"Amazon","META":"Meta",
    "TSLA":"Tesla","NFLX":"Netflix","CRM":"Salesforce","ORCL":"Oracle",
    "PLTR":"Palantir","COIN":"Coinbase","SHOP":"Shopify",
    "LLY":"Eli Lilly","ABBV":"AbbVie","ISRG":"Intuitive",
    "COST":"Costco","WMT":"Walmart","XOM":"ExxonMobil","CVX":"Chevron",
    "JPM":"JPMorgan","GS":"Goldman","V":"Visa","CAT":"Caterpillar","GE":"GE Aero",
    "CRWD":"CrowdStrike","PANW":"Palo Alto",
    "688256.SS":"Cambricon","603019.SS":"Zhongke Shuguang","688012.SS":"SMIC",
    "002371.SZ":"Naura Tech","300474.SZ":"Kingdee",
    "300750.SZ":"CATL","002594.SZ":"BYD","300274.SZ":"Sungrow",
    "601899.SS":"Zijin Mining","603993.SS":"Luoyang Moly","601600.SS":"Aluminum Corp",
    "600519.SS":"Moutai","601985.SS":"CRPC Nuclear","600900.SS":"CYPC Hydro",
}

async def main():
    CAPITAL = 1_000_000
    print("\n" + "="*110)
    print("  QUANT-ONLY vs LLM-ENHANCED STOCK PICKING")
    print("="*110)

    # Load data
    stocks = []
    for ticker, name in STOCKS.items():
        h = fetch(ticker, "5y")
        if h: stocks.append({"ticker": ticker, "name": name, "h": h})
    print(f"  {len(stocks)} stocks loaded.\n")

    # Pure quant ranking
    picker = MultiFactorPicker(use_fundamentals=True)
    quant_rankings = []
    for d in stocks:
        a = picker.analyze(d["ticker"], d["h"], d["name"])
        quant_rankings.append({"ticker": d["ticker"], "name": d["name"],
                               "h": d["h"], "score": a.score, "conviction": a.conviction.value})

    quant_rankings.sort(key=lambda x: x["score"], reverse=True)

    # LLM-enhanced ranking
    llm = LLMStockAnalyzer()
    enhanced_rankings = llm.rank_with_disruption(quant_rankings)

    # Compare
    print(f"  {'#':<4} {'Quant Rank':<25} {'Score':>6} | {'LLM-Enhanced Rank':<25} {'Adj Score':>9} {'Change':>7}")
    print("  " + "-"*90)
    for i in range(min(20, len(quant_rankings))):
        q = quant_rankings[i]
        e = enhanced_rankings[i]
        # Find where quant stock ended up in enhanced
        q_in_e = next((j for j,x in enumerate(enhanced_rankings) if x["ticker"]==q["ticker"]), -1)
        e_in_q = next((j for j,x in enumerate(quant_rankings) if x["ticker"]==e["ticker"]), -1)

        q_label = f"{q['name']}"
        e_label = f"{e['name']}"
        change = e.get("score_change", 0)
        chg_str = f"{change:+.3f}" if change != 0 else "  —"

        print(f"  {i+1:<4} {q_label:<25} {q['score']:>+5.3f} | {e_label:<25} {e['ai_adjusted_score']:>+8.3f} {chg_str}")

    # Key movers
    print(f"\n  --- BIGGEST MOVERS (Quant -> LLM-Enhanced) ---")
    for e in sorted(enhanced_rankings, key=lambda x: x.get("score_change",0), reverse=True)[:5]:
        q_rank = next((i+1 for i,x in enumerate(quant_rankings) if x["ticker"]==e["ticker"]), 0)
        e_rank = next((i+1 for i,x in enumerate(enhanced_rankings) if x["ticker"]==e["ticker"]), 0)
        print(f"  UP   {e['name']:<20} #{q_rank} -> #{e_rank} ({e.get('score_change',0):+.3f})")

    for e in sorted(enhanced_rankings, key=lambda x: x.get("score_change",0))[:5]:
        q_rank = next((i+1 for i,x in enumerate(quant_rankings) if x["ticker"]==e["ticker"]), 0)
        e_rank = next((i+1 for i,x in enumerate(enhanced_rankings) if x["ticker"]==e["ticker"]), 0)
        print(f"  DOWN {e['name']:<20} #{q_rank} -> #{e_rank} ({e.get('score_change',0):+.3f})")

    # Backtest comparison: Top-10 Quant vs Top-10 LLM-Enhanced
    print(f"\n" + "="*110)
    print("  BACKTEST: Top-10 Quant-Only vs Top-10 LLM-Enhanced")
    print("="*110)

    for label, rankings in [("QUANT-ONLY", quant_rankings), ("LLM-ENHANCED", enhanced_rankings)]:
        top10 = rankings[:10]
        total_pnl = 0
        cap_each = CAPITAL / 10
        holdings = []
        for item in top10:
            bt = BacktesterV7(initial_capital=cap_each)
            r = await bt.run(item["ticker"], "v7", item["h"])
            total_pnl += cap_each * r.total_return
            holdings.append(f"{item['name']}({r.total_return:+.0%})")

        port_ret = total_pnl / CAPITAL
        ann = (1+port_ret)**(1/5)-1 if port_ret>-1 else -1
        print(f"\n  {label}:")
        print(f"    Holdings: {', '.join(holdings)}")
        print(f"    5Y Return: {port_ret:+.1%} | Annual: {ann:+.1%}/y | P&L: {total_pnl:+,.0f}")

    print("="*110)

asyncio.run(main())
