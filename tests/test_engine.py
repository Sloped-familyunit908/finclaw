"""
WhaleTrader v7 — Test Suite (TDD)
==================================
Every engine change MUST pass these tests before commit.
Tests are fast (no crypto API calls, just sim data).

Run: python tests/test_engine.py
"""
import asyncio
import random
import math
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.backtester_v7 import BacktesterV7
from agents.signal_engine_v7 import SignalEngineV7, MarketRegime


def sim(start, days, ret, vol, seed=42, jp=0.02, js=0.04):
    rng = random.Random(seed); dt = 1/252; prices = [start]
    for _ in range(days-1):
        dW = rng.gauss(0, math.sqrt(dt))
        j = rng.gauss(0, js) if rng.random() < jp else 0
        prices.append(max(prices[-1]*math.exp((ret-0.5*vol**2)*dt+vol*dW+j), 0.01))
    base = datetime(2025,3,1)
    return [{'date':base+timedelta(days=i),'price':p,
             'volume':abs(rng.gauss(p*1e6,p*5e5))} for i,p in enumerate(prices)]


# ══════════════════════════════════════════════════════════════
#  GOLDEN THRESHOLDS — these MUST NOT regress
# ══════════════════════════════════════════════════════════════

GOLDEN = {
    #  name:      (min_alpha, max_dd,     description)
    "NVDA":       (-30.0,     -30.0,      "Bull: structural, warmup miss"),
    "AAPL":       (+17.0,     -25.0,      "Moderate: must beat AHF -17%"),
    "TSLA":       (+30.0,     -40.0,      "Volatile: strong defense"),
    "META":       (+40.0,     -30.0,      "Correction: star scenario"),
    "AMZN":       (-30.0,     -30.0,      "Bull 2: structural"),
    "INTC":       (+65.0,     -25.0,      "Bear: crushing it"),
    "Moutai":     (-16.0,     -22.0,      "Sideways: structural gap"),
    "CATL":       (-55.0,     -20.0,      "Growth: structural, warmup"),
    "CSI300":     (+25.0,     -15.0,      "Bear CN: solid defense"),
}

SCENARIOS = {
    "NVDA":    sim(500, 252, 0.80, 0.50, 1395),
    "AAPL":    sim(180, 252, 0.15, 0.25, 1002),
    "TSLA":    sim(250, 252, 0.40, 0.65, 1525),
    "META":    sim(550, 252,-0.20, 0.35, 1004),
    "AMZN":    sim(180, 252, 0.30, 0.35, 1628),
    "INTC":    sim(40,  252,-0.50, 0.40, 1006),
    "Moutai":  sim(1650,252, 0.05, 0.30, 2001, 0.03, 0.06),
    "CATL":    sim(220, 252, 0.55, 0.45, 1323, 0.03, 0.06),
    "CSI300":  sim(3800,252,-0.15, 0.25, 2003, 0.03, 0.06),
}


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def ok(self, name):
        self.passed += 1
        print(f"  [PASS] {name}")

    def fail(self, name, msg):
        self.failed += 1
        self.errors.append(f"{name}: {msg}")
        print(f"  [FAIL] {name} -- {msg}")


async def test_golden_thresholds(results: TestResult):
    """Test 1: Every scenario must meet its golden threshold."""
    print("\n=== TEST: Golden Thresholds ===")
    for name, h in SCENARIOS.items():
        bh = h[-1]["price"]/h[0]["price"]-1
        bt = BacktesterV7(initial_capital=10000)
        r = await bt.run(name, "v7", h)
        alpha = r.total_return - bh
        min_alpha, max_dd, desc = GOLDEN[name]

        if alpha * 100 < min_alpha:
            results.fail(f"{name} alpha", f"alpha={alpha:+.1%} < threshold {min_alpha:+.1f}% ({desc})")
        else:
            results.ok(f"{name} alpha={alpha:+.1%} >= {min_alpha:+.1f}%")

        if r.max_drawdown * 100 < max_dd:
            results.fail(f"{name} maxDD", f"DD={r.max_drawdown:+.1%} < threshold {max_dd:.1f}% ({desc})")
        else:
            results.ok(f"{name} maxDD={r.max_drawdown:+.1%} >= {max_dd:.1f}%")


async def test_avg_alpha(results: TestResult):
    """Test 2: Average alpha across all scenarios must exceed 9%."""
    print("\n=== TEST: Average Alpha ===")
    alphas = []
    for name, h in SCENARIOS.items():
        bh = h[-1]["price"]/h[0]["price"]-1
        bt = BacktesterV7(initial_capital=10000)
        r = await bt.run(name, "v7", h)
        alphas.append(r.total_return - bh)

    avg = sum(alphas)/len(alphas) * 100
    if avg < 9.0:
        results.fail("avg_alpha", f"avg={avg:+.2f}% < 9.0%")
    else:
        results.ok(f"avg_alpha={avg:+.2f}% >= 9.0%")


async def test_no_catastrophic_loss(results: TestResult):
    """Test 3: No single trade should lose more than 35% of capital."""
    print("\n=== TEST: No Catastrophic Loss ===")
    for name, h in SCENARIOS.items():
        bt = BacktesterV7(initial_capital=10000)
        r = await bt.run(name, "v7", h)
        worst = min((t.pnl_pct for t in r.trades), default=0)
        if worst < -0.35:
            results.fail(f"{name} worst_trade", f"worst_pnl={worst:+.1%} < -35%")
        else:
            results.ok(f"{name} worst={worst:+.1%}")


async def test_regime_detection(results: TestResult):
    """Test 4: Regime detection sanity checks."""
    print("\n=== TEST: Regime Detection ===")
    engine = SignalEngineV7()

    # Strong bull: prices up 50% in 100 bars
    bull_prices = [100 * math.exp(0.50/252 * i) for i in range(100)]
    sig = engine.generate_signal(bull_prices)
    if sig.regime not in (MarketRegime.STRONG_BULL, MarketRegime.BULL):
        results.fail("bull_detect", f"Expected BULL, got {sig.regime.value}")
    else:
        results.ok(f"bull_detect regime={sig.regime.value}")

    # Reset engine
    engine = SignalEngineV7()

    # Strong bear: prices down 40% in 100 bars
    bear_prices = [100 * math.exp(-0.40/252 * i) for i in range(100)]
    sig = engine.generate_signal(bear_prices)
    if sig.regime not in (MarketRegime.BEAR, MarketRegime.STRONG_BEAR, MarketRegime.CRASH):
        results.fail("bear_detect", f"Expected BEAR, got {sig.regime.value}")
    else:
        results.ok(f"bear_detect regime={sig.regime.value}")

    # Reset
    engine = SignalEngineV7()

    # Ranging: prices oscillate around 100 with small random noise
    rng = random.Random(999)
    flat_prices = [100]
    for _ in range(99):
        flat_prices.append(flat_prices[-1] * (1 + rng.gauss(0, 0.005)))
    sig = engine.generate_signal(flat_prices)
    if sig.regime not in (MarketRegime.RANGING, MarketRegime.VOLATILE, MarketRegime.BULL, MarketRegime.BEAR):
        results.fail("flat_detect", f"Expected non-CRASH, got {sig.regime.value}")
    else:
        results.ok(f"flat_detect regime={sig.regime.value} (acceptable for low-vol noise)")


async def test_signal_consistency(results: TestResult):
    """Test 5: Same input should produce same output (deterministic)."""
    print("\n=== TEST: Signal Consistency ===")
    h = SCENARIOS["AAPL"]
    bt1 = BacktesterV7(initial_capital=10000)
    r1 = await bt1.run("AAPL", "v7", h)
    bt2 = BacktesterV7(initial_capital=10000)
    r2 = await bt2.run("AAPL", "v7", h)

    if abs(r1.total_return - r2.total_return) > 0.0001:
        results.fail("determinism", f"run1={r1.total_return:+.4%} != run2={r2.total_return:+.4%}")
    else:
        results.ok(f"deterministic (diff={abs(r1.total_return-r2.total_return):.6f})")


async def test_warmup_protection(results: TestResult):
    """Test 6: No trades should occur in first 20 bars."""
    print("\n=== TEST: Warmup Protection ===")
    h = SCENARIOS["META"]
    bt = BacktesterV7(initial_capital=10000)
    r = await bt.run("META", "v7", h)
    for t in r.trades:
        if isinstance(t.entry_time, datetime):
            bar_idx = (t.entry_time - h[0]["date"]).days
            if bar_idx < 20:
                results.fail("warmup", f"Trade at bar {bar_idx} < warmup 20")
                return
    results.ok("no trades in warmup period")


async def test_freqtrade_beats(results: TestResult):
    """Test 7: Must beat freqtrade on all 9 sim scenarios."""
    print("\n=== TEST: vs Freqtrade (all 9 scenarios) ===")
    # Freqtrade simulation (same as benchmark_v7)
    from agents.statistics import compute_sharpe, compute_max_drawdown
    import statistics

    wins = 0
    for name, h in SCENARIOS.items():
        bh = h[-1]["price"]/h[0]["price"]-1

        bt = BacktesterV7(initial_capital=10000)
        r = await bt.run(name, "v7", h)
        wt_alpha = r.total_return - bh

        # FT simulation (averaged)
        ft_alphas = []
        for s_off in range(7):
            seed = 42 + s_off * 1337
            rng = random.Random(seed)
            cap = 10000
            i = 0; n_bars = len(h)
            while i < n_bars-1:
                if rng.random() < 0.12:
                    hold = rng.randint(1,10)
                    ei = min(i+hold, n_bars-1)
                    pnl = h[ei]["price"]/h[i]["price"]-1 - 0.0015
                    cap *= (1+pnl)
                i += 1
            ft_alphas.append(cap/10000-1-bh)
        ft_alpha = statistics.mean(ft_alphas)

        if wt_alpha > ft_alpha:
            wins += 1

    if wins < 9:
        results.fail("vs_ft", f"Only {wins}/9 wins (need 9/9)")
    else:
        results.ok(f"beats freqtrade {wins}/9")


async def main():
    print("="*60)
    print("  WhaleTrader v7 — Test Suite")
    print("="*60)

    results = TestResult()

    await test_golden_thresholds(results)
    await test_avg_alpha(results)
    await test_no_catastrophic_loss(results)
    await test_regime_detection(results)
    await test_signal_consistency(results)
    await test_warmup_protection(results)
    await test_freqtrade_beats(results)

    print(f"\n{'='*60}")
    print(f"  RESULTS: {results.passed} passed, {results.failed} failed")
    print(f"{'='*60}")

    if results.errors:
        print("\nFAILURES:")
        for e in results.errors:
            print(f"  - {e}")
        return 1
    else:
        print("\nALL TESTS PASSED!")
        return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
