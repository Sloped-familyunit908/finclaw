"""Test new sectors: optical module, PCB, commercial space, AI apps"""
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging, warnings
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore")

from agents.backtester_v7 import BacktesterV7
from agents.universe import (
    A_SHARES_EXTENDED, US_EXTENDED, HK_EXTENDED,
    SECTOR_LINKAGE, get_linked_stocks
)

try:
    import yfinance as yf
except:
    print("pip install yfinance"); sys.exit(1)

class R:
    def __init__(self): self.p=0;self.f=0;self.e=[]
    def ok(self,n): self.p+=1;print(f"  [PASS] {n}")
    def fail(self,n,m): self.f+=1;self.e.append(f"{n}:{m}");print(f"  [FAIL] {n}:{m}")

def fetch(ticker):
    try:
        df = yf.Ticker(ticker).history(period="1y")
        if df.empty or len(df) < 60: return None
        return [{"date": idx.to_pydatetime(), "price": float(row["Close"]),
                 "volume": float(row["Volume"])} for idx, row in df.iterrows()]
    except: return None

async def main():
    r = R()
    print("="*60)
    print("  FinClaw — New Sectors Test")
    print("="*60)

    # Test universe sizes
    print("\n--- Universe Sizes ---")
    for name, univ in [("US", US_EXTENDED), ("CN", A_SHARES_EXTENDED), ("HK", HK_EXTENDED)]:
        if len(univ) >= 20:
            r.ok(f"{name} universe: {len(univ)} stocks")
        else:
            r.fail(f"{name} universe", f"only {len(univ)} stocks")

    # Test new A-share sectors exist
    print("\n--- New A-Share Sectors ---")
    new_tickers = {
        "optical_module": ["002281.SZ", "300308.SZ"],
        "pcb": ["002938.SZ", "002916.SZ"],
        "ai_apps": ["688047.SS", "002410.SZ"],
        "space": ["688066.SS", "600118.SS"],
    }
    for sector, tickers in new_tickers.items():
        for t in tickers:
            if t in A_SHARES_EXTENDED:
                r.ok(f"{sector}/{t} in universe")
            else:
                r.fail(f"{sector}/{t}", "not in universe")

    # Test sector linkages
    print("\n--- Sector Linkages ---")
    for name in ["optical_module", "pcb_electronics", "commercial_space", "ai_applications"]:
        if name in SECTOR_LINKAGE:
            link = SECTOR_LINKAGE[name]
            r.ok(f"linkage {name}: corr={link['correlation']}")
        else:
            r.fail(f"linkage {name}", "not found")

    # Test cross-market linkage function
    print("\n--- Cross-Market Linkage ---")
    linked = get_linked_stocks("NVDA")
    if linked and len(linked) > 0:
        total_linked = sum(len(l["linked_tickers"]) for l in linked)
        r.ok(f"NVDA linked to {total_linked} stocks across {len(linked)} sectors")
    else:
        r.fail("NVDA linkage", "no links found")

    linked_cn = get_linked_stocks("002281.SZ")  # Guangxun optical
    if linked_cn:
        r.ok(f"Guangxun(002281) linked: {linked_cn[0]['sector']}")
    else:
        r.fail("002281 linkage", "no links")

    # Test backtest on new sector stocks
    print("\n--- Backtest New Sectors ---")
    test_tickers = {
        "300308.SZ": "Zhongji Innolight (Optical)",
        "002938.SZ": "Shennan Circuits (PCB)",
        "002281.SZ": "Guangxun Tech (Optical)",
    }
    for ticker, name in test_tickers.items():
        h = fetch(ticker)
        if not h:
            r.fail(f"bt/{ticker}", "no data")
            continue
        try:
            bt = BacktesterV7(initial_capital=100000)
            res = await bt.run(ticker, "v7", h)
            bh = h[-1]["price"]/h[0]["price"]-1
            r.ok(f"bt/{ticker} ({name}): WT={res.total_return:+.1%} B&H={bh:+.1%} alpha={res.total_return-bh:+.1%}")
        except Exception as e:
            r.fail(f"bt/{ticker}", str(e)[:60])

    # Test existing stocks NOT broken
    print("\n--- Existing Stocks Still Working ---")
    existing = ["NVDA", "600519.SS", "0700.HK"]
    for ticker in existing:
        h = fetch(ticker)
        if not h:
            r.fail(f"existing/{ticker}", "no data")
            continue
        bt = BacktesterV7(initial_capital=100000)
        res = await bt.run(ticker, "v7", h)
        if -1.0 <= res.total_return <= 10.0 and 0 <= res.win_rate <= 1:
            r.ok(f"existing/{ticker}: ret={res.total_return:+.1%} OK")
        else:
            r.fail(f"existing/{ticker}", "invalid results")

    print(f"\n{'='*60}")
    print(f"  RESULTS: {r.p} passed, {r.f} failed")
    print(f"{'='*60}")
    if r.e:
        for e in r.e: print(f"  - {e}")
        return 1
    print("\nALL NEW SECTOR TESTS PASSED!")
    return 0

if __name__ == "__main__":
    exit(asyncio.run(main()))
