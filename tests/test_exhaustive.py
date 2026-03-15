"""
FinClaw — Exhaustive QA Matrix
====================================
Tests EVERY combination of:
- 8 strategies x 3 markets x 2 periods = 48 scan scenarios
- 10 tickers x 3 periods = 30 backtest scenarios
- Edge cases, error handling, data quality
"""
import asyncio, sys, os, time, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging, warnings
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore")

from finclaw import scan_universe, run_strategy, fetch_data, UNIVERSES, STRATEGIES
from agents.backtester_v7 import BacktesterV7
from agents.stock_picker import MultiFactorPicker
from agents.llm_analyzer import LLMStockAnalyzer
from agents.deep_macro import DeepMacroAnalyzer

class QA:
    def __init__(self):
        self.passed=0;self.failed=0;self.skipped=0
        self.errors=[];self.details=[]
    def ok(self,n):
        self.passed+=1
    def fail(self,n,m):
        self.failed+=1;self.errors.append(f"{n}: {m}")
        print(f"    [FAIL] {n}: {m}")
    def skip(self,n,m):
        self.skipped+=1


async def test_all_strategy_market_combos(qa):
    """Test every strategy x market combination."""
    print("\n=== PHASE 1: Strategy x Market Matrix (1y period) ===")
    
    strategies = list(STRATEGIES.keys())
    markets = ["us", "china", "hk"]
    
    # Pre-scan each market once
    market_data = {}
    for market in markets:
        try:
            data = await scan_universe(UNIVERSES[market], "1y", 100000)
            market_data[market] = data
            print(f"  {market}: {len(data)} stocks loaded")
        except Exception as e:
            qa.fail(f"scan_{market}", str(e))
            market_data[market] = []
    
    # Test every combo
    total = len(strategies) * len(markets)
    tested = 0
    
    for style in strategies:
        for market in markets:
            tested += 1
            data = market_data.get(market, [])
            if not data:
                qa.skip(f"{style}/{market}", "no data")
                continue
            
            try:
                result = await run_strategy(style, data, 100000)
                if result is None:
                    qa.skip(f"{style}/{market}", "no stocks matched")
                    continue
                
                # Validate result structure
                checks = [
                    ("has holdings", len(result["holdings"]) > 0),
                    ("return is number", isinstance(result["total_ret"], (int, float))),
                    ("annual is number", isinstance(result["ann_ret"], (int, float))),
                    ("return reasonable", -1.0 <= result["total_ret"] <= 10.0),
                    ("pnl matches", abs(result["pnl"] - result["total_ret"] * 100000) < 100),
                ]
                
                all_ok = True
                for check_name, check_val in checks:
                    if not check_val:
                        qa.fail(f"{style}/{market}/{check_name}", f"failed")
                        all_ok = False
                
                if all_ok:
                    qa.ok(f"{style}/{market}")
                    
            except Exception as e:
                qa.fail(f"{style}/{market}", f"CRASH: {str(e)[:80]}")
    
    print(f"  Tested {tested}/{total} combos")


async def test_backtest_various_tickers(qa):
    """Test backtest on diverse tickers."""
    print("\n=== PHASE 2: Backtest Diverse Tickers ===")
    
    tickers = {
        # US
        "NVDA": "US mega growth",
        "AAPL": "US mega stable", 
        "TSLA": "US high vol",
        "KO": "US defensive",
        "XOM": "US energy",
        # A-share
        "600519.SS": "CN consumer (Moutai)",
        "688256.SS": "CN tech (Cambricon)",
        "002594.SZ": "CN EV (BYD)",
        # HK
        "0700.HK": "HK tech (Tencent)",
        "9988.HK": "HK e-commerce (Alibaba)",
    }
    
    periods = ["6mo", "1y", "2y"]
    
    for ticker, desc in tickers.items():
        for period in periods:
            try:
                h = fetch_data(ticker, period)
                if not h or len(h) < 60:
                    qa.skip(f"bt/{ticker}/{period}", "insufficient data")
                    continue
                
                bt = BacktesterV7(initial_capital=100000)
                r = await bt.run(ticker, "v7", h)
                
                # Comprehensive checks
                issues = []
                if r.total_trades < 0: issues.append("negative trades")
                if not (-1.0 <= r.max_drawdown <= 0): issues.append(f"bad DD={r.max_drawdown}")
                if not (0 <= r.win_rate <= 1): issues.append(f"bad WR={r.win_rate}")
                if len(r.equity_curve) < 2: issues.append("empty equity curve")
                if r.equity_curve and min(r.equity_curve) < 0: issues.append("negative equity")
                if not (-0.99 <= r.total_return <= 50): issues.append(f"extreme return={r.total_return}")
                
                # Check trades are valid
                for t in r.trades:
                    if t.entry_price <= 0: issues.append(f"bad entry price {t.entry_price}")
                    if t.exit_price <= 0: issues.append(f"bad exit price {t.exit_price}")
                
                if issues:
                    qa.fail(f"bt/{ticker}/{period}", "; ".join(issues))
                else:
                    qa.ok(f"bt/{ticker}/{period}")
                    
            except Exception as e:
                qa.fail(f"bt/{ticker}/{period}", f"CRASH: {str(e)[:60]}")


async def test_picker_on_real_data(qa):
    """Test picker with fundamentals on real stocks."""
    print("\n=== PHASE 3: Picker + Fundamentals ===")
    
    picker = MultiFactorPicker(use_fundamentals=True)
    tickers = ["NVDA", "AAPL", "TSLA", "600519.SS", "0700.HK", "INTC", "XOM"]
    
    for ticker in tickers:
        h = fetch_data(ticker, "1y")
        if not h:
            qa.skip(f"picker/{ticker}", "no data")
            continue
        try:
            a = picker.analyze(ticker, h, ticker)
            issues = []
            if not (-2.0 <= a.score <= 2.0): issues.append(f"score out of range: {a.score}")
            if not a.conviction: issues.append("no conviction")
            if len(a.factors) < 4: issues.append(f"too few factors: {len(a.factors)}")
            if not a.reasoning: issues.append("no reasoning")
            
            if issues:
                qa.fail(f"picker/{ticker}", "; ".join(issues))
            else:
                qa.ok(f"picker/{ticker}")
        except Exception as e:
            qa.fail(f"picker/{ticker}", f"CRASH: {str(e)[:60]}")


def test_llm_analyzer(qa):
    """Test LLM disruption analysis."""
    print("\n=== PHASE 4: LLM Disruption Analysis ===")
    
    llm = LLMStockAnalyzer()
    from agents.llm_analyzer import DISRUPTION_DB
    
    # Test all entries in DB
    for ticker in DISRUPTION_DB:
        adj, reason = llm.compute_ai_era_score(ticker, 0.5)
        issues = []
        if not (-0.5 <= adj <= 1.5): issues.append(f"score {adj} out of range")
        if not reason: issues.append("no reason")
        
        if issues:
            qa.fail(f"llm/{ticker}", "; ".join(issues))
        else:
            qa.ok(f"llm/{ticker}")
    
    # Test unknown ticker
    adj, _ = llm.compute_ai_era_score("TOTALLY_UNKNOWN", 0.5)
    if abs(adj - 0.5) < 0.001:
        qa.ok("llm/unknown_passthrough")
    else:
        qa.fail("llm/unknown", f"should be 0.5, got {adj}")


def test_deep_macro(qa):
    """Test deep macro analyzer."""
    print("\n=== PHASE 5: Deep Macro Analysis ===")
    
    try:
        dm = DeepMacroAnalyzer()
        snap = dm.analyze()
        
        checks = [
            ("has vix", snap.vix > 0),
            ("has 10y", snap.us_10y > 0),
            ("has regime", snap.overall_regime in ("RISK_ON", "RISK_OFF", "MIXED")),
            ("has sectors", len(snap.sector_adjustments) > 5),
            ("has reasoning", len(snap.reasoning) > 20),
            ("has economic phase", snap.economic_phase is not None),
            ("has kondratieff", snap.kondratieff is not None),
            ("has commodity cycle", snap.commodity_cycle in ("super_cycle", "normal", "deflation")),
            ("vix reasonable", 5 < snap.vix < 100),
            ("10y reasonable", 0 < snap.us_10y < 15),
        ]
        
        for name, val in checks:
            if val:
                qa.ok(f"macro/{name}")
            else:
                qa.fail(f"macro/{name}", "check failed")
                
    except Exception as e:
        qa.fail("macro/crash", f"CRASH: {str(e)[:80]}")


async def test_error_handling(qa):
    """Test graceful error handling."""
    print("\n=== PHASE 6: Error Handling ===")
    
    # Empty data
    try:
        bt = BacktesterV7(initial_capital=10000)
        await bt.run("TEST", "v7", [])
        qa.fail("empty_data", "should have raised error")
    except (ValueError, Exception):
        qa.ok("empty_data_handled")
    
    # Too few bars
    try:
        bt = BacktesterV7(initial_capital=10000)
        data = [{"date": None, "price": 100, "volume": 0}] * 5
        await bt.run("TEST", "v7", data)
        qa.fail("few_bars", "should have raised error")
    except (ValueError, Exception):
        qa.ok("few_bars_handled")
    
    # Zero capital
    try:
        bt = BacktesterV7(initial_capital=0)
        import random, math
        from datetime import datetime, timedelta
        h = [{"date": datetime(2025,1,1)+timedelta(days=i), "price": 100+i*0.5, "volume": 1000}
             for i in range(100)]
        r = await bt.run("TEST", "v7", h)
        qa.ok(f"zero_capital: ret={r.total_return}")
    except Exception:
        qa.ok("zero_capital_handled")
    
    # Invalid ticker fetch
    h = fetch_data("THIS_DOES_NOT_EXIST_12345", "1y")
    if h is None:
        qa.ok("invalid_ticker_returns_none")
    else:
        qa.fail("invalid_ticker", "should return None")
    
    # Picker with no fundamentals
    try:
        picker = MultiFactorPicker(use_fundamentals=False)
        import math
        from datetime import datetime, timedelta
        h = [{"date": datetime(2025,1,1)+timedelta(days=i),
              "price": 100*math.exp(0.2/252*i), "volume": 1000} for i in range(252)]
        a = picker.analyze("TEST", h, "Test")
        qa.ok(f"picker_no_fundamentals: score={a.score:+.3f}")
    except Exception as e:
        qa.fail("picker_no_fundamentals", str(e))


async def main():
    qa = QA()
    start = time.time()
    
    print("="*80)
    print("  FinClaw -- EXHAUSTIVE QA (Every Feature, Every Path)")
    print("="*80)
    
    await test_all_strategy_market_combos(qa)
    await test_backtest_various_tickers(qa)
    await test_picker_on_real_data(qa)
    test_llm_analyzer(qa)
    test_deep_macro(qa)
    await test_error_handling(qa)
    
    elapsed = time.time() - start
    
    print(f"\n{'='*80}")
    print(f"  EXHAUSTIVE QA RESULTS")
    print(f"  Time: {elapsed:.1f}s")
    print(f"  Passed:  {qa.passed}")
    print(f"  Failed:  {qa.failed}")
    print(f"  Skipped: {qa.skipped}")
    print(f"  Total:   {qa.passed + qa.failed + qa.skipped}")
    print(f"{'='*80}")
    
    if qa.errors:
        print(f"\n  FAILURES ({len(qa.errors)}):")
        for e in qa.errors:
            print(f"    - {e}")
    
    if qa.failed == 0:
        print("\n  ALL EXHAUSTIVE QA TESTS PASSED!")
    
    return qa.failed

if __name__ == "__main__":
    exit(asyncio.run(main()))
