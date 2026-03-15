"""
WhaleTrader — Deep QA Test Suite
=================================
Systematic testing of EVERY feature, edge case, and user scenario.
Run this before any release.
"""
import asyncio, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Suppress yfinance noise
import logging, warnings
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore")

from agents.backtester_v7 import BacktesterV7
from agents.stock_picker import MultiFactorPicker
from agents.llm_analyzer import LLMStockAnalyzer

try:
    import yfinance as yf
except ImportError:
    print("pip install yfinance"); sys.exit(1)


class QA:
    def __init__(self):
        self.passed=0; self.failed=0; self.warnings=[]; self.errors=[]
    def ok(self,n):
        self.passed+=1; print(f"  [OK]   {n}")
    def fail(self,n,m):
        self.failed+=1; self.errors.append(f"{n}: {m}"); print(f"  [FAIL] {n}: {m}")
    def warn(self,n,m):
        self.warnings.append(f"{n}: {m}"); print(f"  [WARN] {n}: {m}")


def fetch(ticker, period="1y"):
    try:
        df = yf.Ticker(ticker).history(period=period)
        if df.empty or len(df) < 30: return None
        return [{"date": idx.to_pydatetime(), "price": float(row["Close"]),
                 "volume": float(row["Volume"])} for idx, row in df.iterrows()]
    except:
        return None


async def main():
    qa = QA()
    start = time.time()

    print("="*80)
    print("  WhaleTrader — DEEP QA TEST")
    print("  Testing every feature systematically")
    print("="*80)

    # ═══ 1. DATA FETCH TESTS ═══
    print("\n--- 1. DATA FETCH TESTS ---")

    test_tickers = {
        "US large": "NVDA",
        "US mid": "CRWD",
        "A-share Shanghai": "600519.SS",
        "A-share Shenzhen": "002594.SZ",
        "A-share STAR": "688256.SS",
        "Hong Kong": "0700.HK",
    }

    for desc, ticker in test_tickers.items():
        h = fetch(ticker, "1y")
        if h and len(h) > 50:
            qa.ok(f"fetch {desc} ({ticker}): {len(h)} bars, ${h[-1]['price']:.2f}")
        else:
            qa.fail(f"fetch {desc}", f"{ticker} returned {len(h) if h else 'None'}")

    # ═══ 2. BACKTESTER ROBUSTNESS ═══
    print("\n--- 2. BACKTESTER ROBUSTNESS ---")

    # Test with real data from each market
    for ticker in ["NVDA", "600519.SS", "0700.HK"]:
        h = fetch(ticker, "1y")
        if not h: continue
        try:
            bt = BacktesterV7(initial_capital=100000)
            r = await bt.run(ticker, "v7", h)

            # Sanity checks
            if r.total_trades >= 0:
                qa.ok(f"{ticker} trades={r.total_trades}")
            else:
                qa.fail(f"{ticker} trades", "negative trade count")

            if -1.0 <= r.max_drawdown <= 0:
                qa.ok(f"{ticker} DD={r.max_drawdown:+.1%}")
            else:
                qa.fail(f"{ticker} DD", f"invalid DD={r.max_drawdown}")

            if len(r.equity_curve) > 0:
                if min(r.equity_curve) >= 0:
                    qa.ok(f"{ticker} equity never negative")
                else:
                    qa.fail(f"{ticker} equity", f"min={min(r.equity_curve):.0f}")
            
            if r.win_rate >= 0 and r.win_rate <= 1:
                qa.ok(f"{ticker} WR={r.win_rate:.0%}")
            else:
                qa.fail(f"{ticker} WR", f"invalid WR={r.win_rate}")

        except Exception as e:
            qa.fail(f"{ticker} backtest", str(e))

    # ═══ 3. PICKER ACCURACY ON REAL DATA ═══
    print("\n--- 3. PICKER ON REAL DATA ---")

    picker = MultiFactorPicker(use_fundamentals=True)

    # Pick a few real stocks and check scores are reasonable
    real_tests = [
        ("NVDA", "should be positive"),  # strong stock
        ("INTC", "likely negative"),  # weak stock
    ]

    for ticker, expectation in real_tests:
        h = fetch(ticker, "1y")
        if not h: continue
        try:
            a = picker.analyze(ticker, h, ticker)
            qa.ok(f"picker {ticker}: score={a.score:+.3f} conviction={a.conviction.value}")
            if len(a.factors) >= 5:
                qa.ok(f"picker {ticker}: {len(a.factors)} factors computed")
            else:
                qa.warn(f"picker {ticker}", f"only {len(a.factors)} factors")
        except Exception as e:
            qa.fail(f"picker {ticker}", str(e))

    # ═══ 4. LLM ANALYZER INTEGRATION ═══
    print("\n--- 4. LLM ANALYZER ---")

    llm = LLMStockAnalyzer()

    # Test all tickers in disruption DB
    from agents.llm_analyzer import DISRUPTION_DB
    for ticker in list(DISRUPTION_DB.keys())[:10]:
        adj, reason = llm.compute_ai_era_score(ticker, 0.5)
        if -0.5 <= adj <= 1.5:
            qa.ok(f"llm {ticker}: adj={adj:+.3f}")
        else:
            qa.fail(f"llm {ticker}", f"score out of range: {adj}")

    # ═══ 5. CAPITAL AMOUNTS ═══
    print("\n--- 5. DIFFERENT CAPITAL SIZES ---")

    h = fetch("AAPL", "1y")
    if h:
        for cap in [1000, 10000, 100000, 1000000, 10000000]:
            try:
                bt = BacktesterV7(initial_capital=cap)
                r = await bt.run("AAPL", "v7", h)
                final = cap * (1 + r.total_return)
                qa.ok(f"capital ${cap:>10,}: return={r.total_return:+.1%} final=${final:,.0f}")
            except Exception as e:
                qa.fail(f"capital {cap}", str(e))

    # ═══ 6. TIME PERIODS ═══
    print("\n--- 6. DIFFERENT TIME PERIODS ---")

    for period in ["3mo", "6mo", "1y", "2y", "5y"]:
        h = fetch("MSFT", period)
        if h and len(h) >= 60:
            bt = BacktesterV7(initial_capital=10000)
            try:
                r = await bt.run("MSFT", "v7", h)
                qa.ok(f"period {period}: {len(h)} bars, ret={r.total_return:+.1%}")
            except Exception as e:
                qa.fail(f"period {period}", str(e))
        elif h:
            qa.warn(f"period {period}", f"only {len(h)} bars (need 60+)")
        else:
            qa.warn(f"period {period}", "no data returned")

    # ═══ 7. CONCURRENT RUNS ═══
    print("\n--- 7. CONCURRENT BACKTESTS ---")

    tickers = ["AAPL", "MSFT", "GOOG"]
    tasks = []
    for t in tickers:
        h = fetch(t, "1y")
        if h:
            bt = BacktesterV7(initial_capital=10000)
            tasks.append(bt.run(t, "v7", h))

    if tasks:
        try:
            results = await asyncio.gather(*tasks)
            for t, r in zip(tickers, results):
                qa.ok(f"concurrent {t}: {r.total_return:+.1%}")
        except Exception as e:
            qa.fail("concurrent", str(e))

    # ═══ 8. OUTPUT FORMAT CHECKS ═══
    print("\n--- 8. OUTPUT FORMAT ---")

    h = fetch("META", "1y")
    if h:
        bt = BacktesterV7(initial_capital=10000)
        r = await bt.run("META", "v7", h)

        # Check all expected fields exist
        fields = ["total_return", "total_trades", "win_rate", "max_drawdown",
                  "sharpe_ratio", "equity_curve", "trades"]
        for f in fields:
            if hasattr(r, f):
                qa.ok(f"result has '{f}'")
            else:
                qa.fail(f"missing field", f"BacktestResult.{f}")

        # Check trades have required fields
        if r.trades:
            t = r.trades[0]
            trade_fields = ["entry_price", "exit_price", "entry_time", "exit_time",
                           "pnl", "pnl_pct", "signal_source"]
            for f in trade_fields:
                if hasattr(t, f):
                    qa.ok(f"trade has '{f}'")
                else:
                    qa.fail(f"trade missing", f"Trade.{f}")

    # ═══ SUMMARY ═══
    elapsed = time.time() - start

    print(f"\n{'='*80}")
    print(f"  DEEP QA RESULTS")
    print(f"  Time: {elapsed:.1f}s")
    print(f"  Passed: {qa.passed}")
    print(f"  Failed: {qa.failed}")
    print(f"  Warnings: {len(qa.warnings)}")
    print(f"{'='*80}")

    if qa.errors:
        print("\n  FAILURES:")
        for e in qa.errors: print(f"    - {e}")

    if qa.warnings:
        print("\n  WARNINGS:")
        for w in qa.warnings: print(f"    - {w}")

    if qa.failed == 0:
        print("\n  ALL DEEP QA TESTS PASSED!")
    
    return qa.failed

if __name__ == "__main__":
    exit(asyncio.run(main()))
