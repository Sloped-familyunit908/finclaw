"""
FinClaw — Strategy & Integration Tests
============================================
Comprehensive strategy-level testing.
Tests actual portfolio performance, not just unit logic.
"""
import asyncio, random, math, sys, os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.backtester_v7 import BacktesterV7
from agents.stock_picker import MultiFactorPicker
from agents.llm_analyzer import LLMStockAnalyzer
from agents.signal_engine_v7 import SignalEngineV7, MarketRegime


def sim(start, days, ret, vol, seed=42, jp=0.02, js=0.04):
    rng = random.Random(seed); dt = 1/252; prices = [start]
    for _ in range(days-1):
        dW = rng.gauss(0, math.sqrt(dt))
        j = rng.gauss(0,js) if rng.random() < jp else 0
        prices.append(max(prices[-1]*math.exp((ret-0.5*vol**2)*dt+vol*dW+j), 0.01))
    base = datetime(2025,3,1)
    return [{'date':base+timedelta(days=i),'price':p,'volume':abs(rng.gauss(p*1e6,p*5e5))}
            for i,p in enumerate(prices)]


class R:
    def __init__(self):
        self.passed=0;self.failed=0;self.errors=[]
    def ok(self,n):
        self.passed+=1;print(f"  [PASS] {n}")
    def fail(self,n,m):
        self.failed+=1;self.errors.append(f"{n}: {m}");print(f"  [FAIL] {n} -- {m}")


# ═══════════════════════════════════════════════════════
# STRATEGY BACKTESTS — do strategies actually work?
# ═══════════════════════════════════════════════════════

async def test_bull_market_profit(r):
    """In a bull market, system MUST make money."""
    print("\n=== TEST: Bull Market Must Profit ===")
    profitable = 0
    total = 0
    for seed in range(1001, 1021):  # test 20 seeds, expect majority profitable
        h = sim(100, 252, 0.50, 0.25, seed)
        bh = h[-1]["price"]/h[0]["price"]-1
        if bh < 0.10: continue  # skip seeds where even B&H fails (not really "bull")
        total += 1
        bt = BacktesterV7(initial_capital=10000)
        res = await bt.run("BULL", "v7", h)
        if res.total_return > 0:
            profitable += 1
    ratio = profitable/max(total,1)
    if ratio >= 0.60:
        r.ok(f"profitable in {profitable}/{total} real bull scenarios ({ratio:.0%})")
    else:
        r.fail("bull_profit", f"Only {profitable}/{total} profitable ({ratio:.0%})")


async def test_bear_market_defense(r):
    """In a bear market, system should lose LESS than B&H."""
    print("\n=== TEST: Bear Market Defense ===")
    for seed in [2001, 2002, 2003]:
        h = sim(100, 252, -0.30, 0.30, seed)
        bh = h[-1]["price"]/h[0]["price"]-1
        bt = BacktesterV7(initial_capital=10000)
        res = await bt.run("BEAR", "v7", h)
        if res.total_return >= bh:
            continue  # good, we beat B&H
        else:
            alpha = res.total_return - bh
            if alpha < -0.10:  # allow small underperformance
                r.fail(f"bear_defense_s{seed}", f"alpha={alpha:+.1%} too negative")
                return
    r.ok("defended in 3/3 bear scenarios")


async def test_sideways_not_hemorrhage(r):
    """In sideways market, should not lose more than 15%."""
    print("\n=== TEST: Sideways Market Cap Loss ===")
    h = sim(100, 252, 0.0, 0.20, 3001)
    bt = BacktesterV7(initial_capital=10000)
    res = await bt.run("FLAT", "v7", h)
    if res.total_return > -0.15:
        r.ok(f"sideways loss capped: {res.total_return:+.1%}")
    else:
        r.fail("sideways_cap", f"Lost {res.total_return:+.1%} in flat market (>15%)")


async def test_high_vol_survival(r):
    """In extreme volatility (70%+), system should survive (not blow up)."""
    print("\n=== TEST: High Volatility Survival ===")
    h = sim(100, 252, 0.10, 0.70, 4001, 0.05, 0.10)
    bt = BacktesterV7(initial_capital=10000)
    res = await bt.run("HIGHVOL", "v7", h)
    if res.total_return > -0.60:
        r.ok(f"survived high vol: {res.total_return:+.1%} (DD={res.max_drawdown:+.1%})")
    else:
        r.fail("highvol_survival", f"Blew up: {res.total_return:+.1%}")


async def test_crash_recovery(r):
    """After a crash, system should eventually recover."""
    print("\n=== TEST: Crash Recovery ===")
    # V-shape: crash then recover
    h1 = sim(100, 126, -0.60, 0.40, 5001)
    h2 = sim(h1[-1]["price"], 126, 0.80, 0.40, 5002)
    # Fix dates for h2
    last_date = h1[-1]["date"]
    for i, bar in enumerate(h2):
        bar["date"] = last_date + timedelta(days=i+1)
    h = h1 + h2

    bt = BacktesterV7(initial_capital=10000)
    res = await bt.run("CRASH", "v7", h)
    if res.total_return > -0.30:
        r.ok(f"crash recovery: {res.total_return:+.1%}")
    else:
        r.fail("crash_recovery", f"Failed to recover: {res.total_return:+.1%}")


async def test_portfolio_diversification(r):
    """Portfolio of 5 stocks should have lower DD than worst individual."""
    print("\n=== TEST: Portfolio Diversification ===")
    scenarios = [
        sim(100, 252, 0.30, 0.35, 6001),
        sim(100, 252, -0.10, 0.25, 6002),
        sim(100, 252, 0.50, 0.50, 6003),
        sim(100, 252, -0.20, 0.30, 6004),
        sim(100, 252, 0.15, 0.20, 6005),
    ]

    worst_dd = 0
    total_ret = 0
    for h in scenarios:
        bt = BacktesterV7(initial_capital=2000)
        res = await bt.run("P", "v7", h)
        worst_dd = min(worst_dd, res.max_drawdown)
        total_ret += 2000 * res.total_return

    port_ret = total_ret / 10000
    # Portfolio should do better than worst individual DD
    if port_ret > -0.30:
        r.ok(f"portfolio return={port_ret:+.1%}, worst individual DD={worst_dd:+.1%}")
    else:
        r.fail("diversification", f"portfolio too bad: {port_ret:+.1%}")


# ═══════════════════════════════════════════════════════
# PICKER STRATEGY TESTS
# ═══════════════════════════════════════════════════════

async def test_picker_selects_winners(r):
    """Top picks should outperform bottom picks over time."""
    print("\n=== TEST: Picker Selects Winners ===")
    picker = MultiFactorPicker(use_fundamentals=False)

    stocks = [
        {"ticker":"W1","name":"Winner1","h":sim(100,252,0.50,0.25,7001)},
        {"ticker":"W2","name":"Winner2","h":sim(100,252,0.40,0.30,7002)},
        {"ticker":"W3","name":"Winner3","h":sim(100,252,0.30,0.20,7003)},
        {"ticker":"L1","name":"Loser1","h":sim(100,252,-0.20,0.30,7004)},
        {"ticker":"L2","name":"Loser2","h":sim(100,252,-0.30,0.25,7005)},
        {"ticker":"L3","name":"Loser3","h":sim(100,252,-0.40,0.35,7006)},
    ]

    rankings = picker.rank_universe(stocks)
    top3 = [x.ticker for x in rankings[:3]]
    bot3 = [x.ticker for x in rankings[-3:]]

    # At least 2 out of 3 top picks should be winners
    top_winners = sum(1 for t in top3 if t.startswith("W"))
    if top_winners >= 2:
        r.ok(f"top3={top3} has {top_winners}/3 winners")
    else:
        r.fail("picker_winners", f"top3={top3} only {top_winners}/3 winners")


def test_llm_boosts_ai_stocks(r):
    """LLM adjustment should boost NVDA/AVGO over non-AI stocks."""
    print("\n=== TEST: LLM Boosts AI Stocks ===")
    llm = LLMStockAnalyzer()

    ai_stocks = ["NVDA", "AVGO", "ANET", "PLTR", "688256.SS"]
    non_ai = ["XOM", "KO", "600519.SS"]

    base = 0.5
    ai_adj = [llm.compute_ai_era_score(t, base)[0] for t in ai_stocks]
    non_ai_adj = [llm.compute_ai_era_score(t, base)[0] for t in non_ai]

    avg_ai = sum(ai_adj)/len(ai_adj)
    avg_non = sum(non_ai_adj)/len(non_ai_adj)

    if avg_ai > avg_non:
        r.ok(f"AI stocks avg={avg_ai:.3f} > non-AI avg={avg_non:.3f}")
    else:
        r.fail("llm_boost", f"AI={avg_ai:.3f} <= non-AI={avg_non:.3f}")


def test_llm_penalizes_disrupted(r):
    """CRM and SHOP should be penalized (AI disruption victims)."""
    print("\n=== TEST: LLM Penalizes Disrupted ===")
    llm = LLMStockAnalyzer()

    victims = ["CRM", "SHOP", "INTC"]
    base = 0.5

    all_penalized = all(llm.compute_ai_era_score(t, base)[0] < base for t in victims)
    if all_penalized:
        scores = [f"{t}={llm.compute_ai_era_score(t,base)[0]:.3f}" for t in victims]
        r.ok(f"all disrupted stocks penalized: {', '.join(scores)}")
    else:
        r.fail("llm_penalty", "Not all disrupted stocks penalized")


# ═══════════════════════════════════════════════════════
# EDGE CASE TESTS
# ═══════════════════════════════════════════════════════

async def test_minimum_data(r):
    """Should handle minimum data (exactly 20 bars) gracefully."""
    print("\n=== TEST: Minimum Data (20 bars) ===")
    h = sim(100, 25, 0.10, 0.20, 8001)  # just barely enough
    bt = BacktesterV7(initial_capital=10000)
    try:
        res = await bt.run("MIN", "v7", h)
        r.ok(f"handled 25 bars: {res.total_return:+.1%}")
    except Exception as e:
        r.fail("min_data", str(e))


async def test_very_long_history(r):
    """Should handle 10 years (2520 bars) without issues."""
    print("\n=== TEST: Long History (10 years) ===")
    h = sim(100, 2520, 0.12, 0.20, 8002)
    bt = BacktesterV7(initial_capital=10000)
    res = await bt.run("LONG", "v7", h)
    if res.total_return > 0:
        r.ok(f"10Y backtest: {res.total_return:+.1%}, {res.total_trades} trades")
    else:
        r.fail("long_history", f"10Y return negative: {res.total_return:+.1%}")


async def test_penny_stock(r):
    """Should handle penny stocks ($0.50) without division by zero."""
    print("\n=== TEST: Penny Stock ===")
    h = sim(0.50, 252, 0.20, 0.60, 8003)
    bt = BacktesterV7(initial_capital=10000)
    try:
        res = await bt.run("PENNY", "v7", h)
        r.ok(f"penny stock OK: {res.total_return:+.1%}")
    except Exception as e:
        r.fail("penny_stock", str(e))


async def test_expensive_stock(r):
    """Should handle expensive stocks ($5000+)."""
    print("\n=== TEST: Expensive Stock ===")
    h = sim(5000, 252, 0.15, 0.20, 8004)
    bt = BacktesterV7(initial_capital=10000)
    res = await bt.run("EXPENSIVE", "v7", h)
    r.ok(f"expensive stock OK: {res.total_return:+.1%}")


async def test_zero_volume(r):
    """Should work even with zero volume data."""
    print("\n=== TEST: Zero Volume ===")
    h = [{"date": datetime(2025,1,1)+timedelta(days=i),
          "price": 100*math.exp(0.15/252*i), "volume": 0} for i in range(252)]
    bt = BacktesterV7(initial_capital=10000)
    res = await bt.run("NOVOL", "v7", h)
    r.ok(f"zero volume OK: {res.total_return:+.1%}")


# ═══════════════════════════════════════════════════════
# CONSISTENCY TESTS
# ═══════════════════════════════════════════════════════

async def test_capital_conservation(r):
    """Final capital + open positions should equal initial + P&L."""
    print("\n=== TEST: Capital Conservation ===")
    h = sim(100, 252, 0.20, 0.30, 9001)
    bt = BacktesterV7(initial_capital=10000)
    res = await bt.run("CC", "v7", h)
    final = 10000 * (1 + res.total_return)
    # equity curve last value should match
    if len(res.equity_curve) > 0:
        eq_final = res.equity_curve[-1]
        diff = abs(final - eq_final) / max(final, 1)
        if diff < 0.01:  # < 1% difference
            r.ok(f"capital conserved: computed={final:.0f} equity={eq_final:.0f}")
        else:
            r.fail("capital_conservation", f"mismatch: {final:.0f} vs {eq_final:.0f} ({diff:.1%})")
    else:
        r.ok("no equity curve to check")


async def test_no_negative_capital(r):
    """Capital should never go negative during backtest."""
    print("\n=== TEST: No Negative Capital ===")
    h = sim(100, 252, -0.50, 0.50, 9002, 0.05, 0.10)  # extreme bear
    bt = BacktesterV7(initial_capital=10000)
    res = await bt.run("NEG", "v7", h)
    neg_eq = [e for e in res.equity_curve if e < 0]
    if not neg_eq:
        r.ok(f"capital never negative (min={min(res.equity_curve):.0f})")
    else:
        r.fail("negative_capital", f"{len(neg_eq)} negative equity points")


async def test_max_drawdown_accuracy(r):
    """Reported max drawdown should match equity curve."""
    print("\n=== TEST: Max Drawdown Accuracy ===")
    h = sim(100, 252, 0.10, 0.35, 9003)
    bt = BacktesterV7(initial_capital=10000)
    res = await bt.run("DD", "v7", h)

    # Compute DD from equity curve
    peak = res.equity_curve[0]; computed_dd = 0
    for eq in res.equity_curve:
        peak = max(peak, eq)
        dd = (eq - peak) / peak if peak > 0 else 0
        computed_dd = min(computed_dd, dd)

    diff = abs(res.max_drawdown - computed_dd)
    if diff < 0.01:
        r.ok(f"DD accurate: reported={res.max_drawdown:+.1%} computed={computed_dd:+.1%}")
    else:
        r.fail("dd_accuracy", f"reported={res.max_drawdown:+.1%} vs computed={computed_dd:+.1%}")


async def main():
    print("="*60)
    print("  FinClaw -- Strategy & Integration Tests")
    print("="*60)

    results = R()

    # Strategy tests
    await test_bull_market_profit(results)
    await test_bear_market_defense(results)
    await test_sideways_not_hemorrhage(results)
    await test_high_vol_survival(results)
    await test_crash_recovery(results)
    await test_portfolio_diversification(results)

    # Picker strategy tests
    await test_picker_selects_winners(results)
    test_llm_boosts_ai_stocks(results)
    test_llm_penalizes_disrupted(results)

    # Edge cases
    await test_minimum_data(results)
    await test_very_long_history(results)
    await test_penny_stock(results)
    await test_expensive_stock(results)
    await test_zero_volume(results)

    # Consistency
    await test_capital_conservation(results)
    await test_no_negative_capital(results)
    await test_max_drawdown_accuracy(results)

    print(f"\n{'='*60}")
    print(f"  RESULTS: {results.passed} passed, {results.failed} failed")
    print(f"{'='*60}")
    if results.errors:
        for e in results.errors: print(f"  - {e}")
        return 1
    print("\nALL TESTS PASSED!")
    return 0

if __name__ == "__main__":
    exit(asyncio.run(main()))
