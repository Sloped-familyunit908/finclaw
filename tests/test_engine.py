"""
FinClaw v7 — Engine Test Suite (TDD)
==================================
Every engine change MUST pass these tests before commit.
Tests are fast (no crypto API calls, just sim data).

Converted from custom test runner to proper pytest.
"""
import asyncio
import random
import math
import sys
import os
import pytest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.backtester_v7 import BacktesterV7
from agents.signal_engine_v7 import SignalEngineV7, MarketRegime


def sim(start, days, ret, vol, seed=42, jp=0.02, js=0.04):
    rng = random.Random(seed)
    dt = 1 / 252
    prices = [start]
    for _ in range(days - 1):
        dW = rng.gauss(0, math.sqrt(dt))
        j = rng.gauss(0, js) if rng.random() < jp else 0
        prices.append(max(prices[-1] * math.exp((ret - 0.5 * vol**2) * dt + vol * dW + j), 0.01))
    base = datetime(2025, 3, 1)
    return [
        {"date": base + timedelta(days=i), "price": p, "volume": abs(rng.gauss(p * 1e6, p * 5e5))}
        for i, p in enumerate(prices)
    ]


# ══════════════════════════════════════════════════════════════
#  GOLDEN THRESHOLDS — these MUST NOT regress
# ══════════════════════════════════════════════════════════════

GOLDEN = {
    "NVDA":   (-30.0, -30.0, "Bull: structural, warmup miss"),
    "AAPL":   (+17.0, -25.0, "Moderate: must beat AHF -17%"),
    "TSLA":   (+30.0, -40.0, "Volatile: strong defense"),
    "META":   (+40.0, -30.0, "Correction: star scenario"),
    "AMZN":   (-30.0, -30.0, "Bull 2: structural"),
    "INTC":   (+65.0, -25.0, "Bear: crushing it"),
    "Moutai": (-16.0, -22.0, "Sideways: structural gap"),
    "CATL":   (-55.0, -20.0, "Growth: structural, warmup"),
    "CSI300": (+25.0, -15.0, "Bear CN: solid defense"),
}

SCENARIOS = {
    "NVDA":   sim(500,  252,  0.80, 0.50, 1395),
    "AAPL":   sim(180,  252,  0.15, 0.25, 1002),
    "TSLA":   sim(250,  252,  0.40, 0.65, 1525),
    "META":   sim(550,  252, -0.20, 0.35, 1004),
    "AMZN":   sim(180,  252,  0.30, 0.35, 1628),
    "INTC":   sim(40,   252, -0.50, 0.40, 1006),
    "Moutai": sim(1650, 252,  0.05, 0.30, 2001, 0.03, 0.06),
    "CATL":   sim(220,  252,  0.55, 0.45, 1323, 0.03, 0.06),
    "CSI300": sim(3800, 252, -0.15, 0.25, 2003, 0.03, 0.06),
}


@pytest.mark.asyncio
@pytest.mark.parametrize("name", list(SCENARIOS.keys()))
async def test_golden_threshold_alpha(name):
    """Each scenario must meet its golden alpha threshold."""
    h = SCENARIOS[name]
    bh = h[-1]["price"] / h[0]["price"] - 1
    bt = BacktesterV7(initial_capital=10000)
    r = await bt.run(name, "v7", h)
    alpha = r.total_return - bh
    min_alpha, _, desc = GOLDEN[name]
    assert alpha * 100 >= min_alpha, (
        f"{name}: alpha={alpha:+.1%} < threshold {min_alpha:+.1f}% ({desc})"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("name", list(SCENARIOS.keys()))
async def test_golden_threshold_maxdd(name):
    """Each scenario must meet its golden max drawdown threshold."""
    h = SCENARIOS[name]
    bt = BacktesterV7(initial_capital=10000)
    r = await bt.run(name, "v7", h)
    _, max_dd, desc = GOLDEN[name]
    assert r.max_drawdown * 100 >= max_dd, (
        f"{name}: DD={r.max_drawdown:+.1%} < threshold {max_dd:.1f}% ({desc})"
    )


@pytest.mark.asyncio
async def test_avg_alpha():
    """Average alpha across all scenarios must exceed 9%."""
    alphas = []
    for name, h in SCENARIOS.items():
        bh = h[-1]["price"] / h[0]["price"] - 1
        bt = BacktesterV7(initial_capital=10000)
        r = await bt.run(name, "v7", h)
        alphas.append(r.total_return - bh)

    avg = sum(alphas) / len(alphas) * 100
    assert avg >= 9.0, f"avg_alpha={avg:+.2f}% < 9.0%"


@pytest.mark.asyncio
async def test_no_catastrophic_loss():
    """No single trade should lose more than 35% of capital."""
    for name, h in SCENARIOS.items():
        bt = BacktesterV7(initial_capital=10000)
        r = await bt.run(name, "v7", h)
        worst = min((t.pnl_pct for t in r.trades), default=0)
        assert worst >= -0.35, f"{name}: worst_pnl={worst:+.1%} < -35%"


@pytest.mark.asyncio
async def test_regime_detection():
    """Regime detection sanity checks for bull, bear, and flat markets."""
    # Strong bull
    engine = SignalEngineV7()
    bull_prices = [100 * math.exp(0.50 / 252 * i) for i in range(100)]
    sig = engine.generate_signal(bull_prices)
    assert sig.regime in (MarketRegime.STRONG_BULL, MarketRegime.BULL), (
        f"Expected BULL regime, got {sig.regime.value}"
    )

    # Strong bear
    engine = SignalEngineV7()
    bear_prices = [100 * math.exp(-0.40 / 252 * i) for i in range(100)]
    sig = engine.generate_signal(bear_prices)
    assert sig.regime in (MarketRegime.BEAR, MarketRegime.STRONG_BEAR, MarketRegime.CRASH), (
        f"Expected BEAR regime, got {sig.regime.value}"
    )

    # Ranging
    engine = SignalEngineV7()
    rng = random.Random(999)
    flat_prices = [100]
    for _ in range(99):
        flat_prices.append(flat_prices[-1] * (1 + rng.gauss(0, 0.005)))
    sig = engine.generate_signal(flat_prices)
    assert sig.regime not in (MarketRegime.CRASH,), (
        f"Expected non-CRASH regime for flat market, got {sig.regime.value}"
    )


@pytest.mark.asyncio
async def test_signal_consistency():
    """Same input should produce same output (deterministic)."""
    h = SCENARIOS["AAPL"]
    bt1 = BacktesterV7(initial_capital=10000)
    r1 = await bt1.run("AAPL", "v7", h)
    bt2 = BacktesterV7(initial_capital=10000)
    r2 = await bt2.run("AAPL", "v7", h)

    assert abs(r1.total_return - r2.total_return) <= 0.0001, (
        f"Not deterministic: run1={r1.total_return:+.4%} != run2={r2.total_return:+.4%}"
    )


@pytest.mark.asyncio
async def test_warmup_protection():
    """No trades should occur in first 20 bars."""
    h = SCENARIOS["META"]
    bt = BacktesterV7(initial_capital=10000)
    r = await bt.run("META", "v7", h)
    for t in r.trades:
        if isinstance(t.entry_time, datetime):
            bar_idx = (t.entry_time - h[0]["date"]).days
            assert bar_idx >= 20, f"Trade at bar {bar_idx} < warmup period 20"


@pytest.mark.asyncio
async def test_freqtrade_beats():
    """Must beat freqtrade simulation on all 9 scenarios."""
    from agents.statistics import compute_sharpe, compute_max_drawdown

    wins = 0
    for name, h in SCENARIOS.items():
        bh = h[-1]["price"] / h[0]["price"] - 1

        bt = BacktesterV7(initial_capital=10000)
        r = await bt.run(name, "v7", h)
        wt_alpha = r.total_return - bh

        # FT simulation (averaged)
        ft_alphas = []
        for s_off in range(7):
            seed = 42 + s_off * 1337
            rng = random.Random(seed)
            cap = 10000
            i = 0
            n_bars = len(h)
            while i < n_bars - 1:
                if rng.random() < 0.12:
                    hold = rng.randint(1, 10)
                    ei = min(i + hold, n_bars - 1)
                    pnl = h[ei]["price"] / h[i]["price"] - 1 - 0.0015
                    cap *= 1 + pnl
                i += 1
            ft_alphas.append(cap / 10000 - 1 - bh)

        import statistics
        ft_alpha = statistics.mean(ft_alphas)

        if wt_alpha > ft_alpha:
            wins += 1

    assert wins >= 9, f"Only {wins}/9 wins vs freqtrade (need 9/9)"
