"""
FinClaw — Strategy & Integration Tests
============================================
Comprehensive strategy-level testing.
Tests actual portfolio performance, not just unit logic.

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
from agents.stock_picker import MultiFactorPicker
from agents.llm_analyzer import LLMStockAnalyzer
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


# ═══════════════════════════════════════════════════════
# STRATEGY BACKTESTS — do strategies actually work?
# ═══════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_bull_market_profit():
    """In a bull market, system MUST make money in majority of seeds."""
    profitable = 0
    total = 0
    for seed in range(1001, 1021):
        h = sim(100, 252, 0.50, 0.25, seed)
        bh = h[-1]["price"] / h[0]["price"] - 1
        if bh < 0.10:
            continue  # skip seeds where even B&H fails
        total += 1
        bt = BacktesterV7(initial_capital=10000)
        res = await bt.run("BULL", "v7", h)
        if res.total_return > 0:
            profitable += 1
    ratio = profitable / max(total, 1)
    assert ratio >= 0.60, f"Only {profitable}/{total} profitable ({ratio:.0%}), need >=60%"


@pytest.mark.asyncio
async def test_bear_market_defense():
    """In a bear market, system should lose LESS than B&H (or close)."""
    for seed in [2001, 2002, 2003]:
        h = sim(100, 252, -0.30, 0.30, seed)
        bh = h[-1]["price"] / h[0]["price"] - 1
        bt = BacktesterV7(initial_capital=10000)
        res = await bt.run("BEAR", "v7", h)
        alpha = res.total_return - bh
        assert alpha >= -0.10, (
            f"seed={seed}: alpha={alpha:+.1%} too negative (system={res.total_return:+.1%}, bh={bh:+.1%})"
        )


@pytest.mark.asyncio
async def test_sideways_not_hemorrhage():
    """In sideways market, should not lose more than 15%."""
    h = sim(100, 252, 0.0, 0.20, 3001)
    bt = BacktesterV7(initial_capital=10000)
    res = await bt.run("FLAT", "v7", h)
    assert res.total_return > -0.15, f"Lost {res.total_return:+.1%} in flat market (>15%)"


@pytest.mark.asyncio
async def test_high_vol_survival():
    """In extreme volatility (70%+), system should survive (not blow up)."""
    h = sim(100, 252, 0.10, 0.70, 4001, 0.05, 0.10)
    bt = BacktesterV7(initial_capital=10000)
    res = await bt.run("HIGHVOL", "v7", h)
    assert res.total_return > -0.60, f"Blew up in high vol: {res.total_return:+.1%}"


@pytest.mark.asyncio
async def test_crash_recovery():
    """After a crash, system should eventually recover."""
    h1 = sim(100, 126, -0.60, 0.40, 5001)
    h2 = sim(h1[-1]["price"], 126, 0.80, 0.40, 5002)
    last_date = h1[-1]["date"]
    for i, bar in enumerate(h2):
        bar["date"] = last_date + timedelta(days=i + 1)
    h = h1 + h2

    bt = BacktesterV7(initial_capital=10000)
    res = await bt.run("CRASH", "v7", h)
    assert res.total_return > -0.30, f"Failed to recover: {res.total_return:+.1%}"


@pytest.mark.asyncio
async def test_portfolio_diversification():
    """Portfolio of 5 stocks should have loss capped at -30%."""
    scenarios = [
        sim(100, 252, 0.30, 0.35, 6001),
        sim(100, 252, -0.10, 0.25, 6002),
        sim(100, 252, 0.50, 0.50, 6003),
        sim(100, 252, -0.20, 0.30, 6004),
        sim(100, 252, 0.15, 0.20, 6005),
    ]

    total_ret = 0
    for h in scenarios:
        bt = BacktesterV7(initial_capital=2000)
        res = await bt.run("P", "v7", h)
        total_ret += 2000 * res.total_return

    port_ret = total_ret / 10000
    assert port_ret > -0.30, f"Portfolio return too bad: {port_ret:+.1%}"


# ═══════════════════════════════════════════════════════
# PICKER STRATEGY TESTS
# ═══════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_picker_selects_winners():
    """Top picks should outperform bottom picks over time."""
    picker = MultiFactorPicker(use_fundamentals=False)

    stocks = [
        {"ticker": "W1", "name": "Winner1", "h": sim(100, 252, 0.50, 0.25, 7001)},
        {"ticker": "W2", "name": "Winner2", "h": sim(100, 252, 0.40, 0.30, 7002)},
        {"ticker": "W3", "name": "Winner3", "h": sim(100, 252, 0.30, 0.20, 7003)},
        {"ticker": "L1", "name": "Loser1", "h": sim(100, 252, -0.20, 0.30, 7004)},
        {"ticker": "L2", "name": "Loser2", "h": sim(100, 252, -0.30, 0.25, 7005)},
        {"ticker": "L3", "name": "Loser3", "h": sim(100, 252, -0.40, 0.35, 7006)},
    ]

    rankings = picker.rank_universe(stocks)
    top3 = [x.ticker for x in rankings[:3]]

    top_winners = sum(1 for t in top3 if t.startswith("W"))
    assert top_winners >= 2, f"top3={top3} has only {top_winners}/3 winners, need >=2"


def test_llm_boosts_ai_stocks():
    """LLM adjustment should boost NVDA/AVGO over non-AI stocks."""
    llm = LLMStockAnalyzer()

    ai_stocks = ["NVDA", "AVGO", "ANET", "PLTR", "688256.SS"]
    non_ai = ["XOM", "KO", "600519.SS"]

    base = 0.5
    ai_adj = [llm.compute_ai_era_score(t, base)[0] for t in ai_stocks]
    non_ai_adj = [llm.compute_ai_era_score(t, base)[0] for t in non_ai]

    avg_ai = sum(ai_adj) / len(ai_adj)
    avg_non = sum(non_ai_adj) / len(non_ai_adj)

    assert avg_ai > avg_non, f"AI stocks avg={avg_ai:.3f} should be > non-AI avg={avg_non:.3f}"


def test_llm_penalizes_disrupted():
    """CRM and SHOP should be penalized (AI disruption victims)."""
    llm = LLMStockAnalyzer()

    victims = ["CRM", "SHOP", "INTC"]
    base = 0.5

    for ticker in victims:
        score, _ = llm.compute_ai_era_score(ticker, base)
        assert score < base, f"{ticker} score={score:.3f} should be penalized below base={base}"


# ═══════════════════════════════════════════════════════
# EDGE CASE TESTS
# ═══════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_minimum_data():
    """Should handle minimum data (25 bars) gracefully."""
    h = sim(100, 25, 0.10, 0.20, 8001)
    bt = BacktesterV7(initial_capital=10000)
    res = await bt.run("MIN", "v7", h)
    assert hasattr(res, "total_return"), "Result should have total_return"
    assert isinstance(res.total_return, (int, float)), "total_return should be numeric"


@pytest.mark.asyncio
async def test_very_long_history():
    """Should handle 10 years (2520 bars) without issues."""
    h = sim(100, 2520, 0.12, 0.20, 8002)
    bt = BacktesterV7(initial_capital=10000)
    res = await bt.run("LONG", "v7", h)
    assert res.total_return > 0, f"10Y return should be positive, got {res.total_return:+.1%}"
    assert res.total_trades > 0, "Should have at least 1 trade over 10 years"


@pytest.mark.asyncio
async def test_penny_stock():
    """Should handle penny stocks ($0.50) without division by zero."""
    h = sim(0.50, 252, 0.20, 0.60, 8003)
    bt = BacktesterV7(initial_capital=10000)
    res = await bt.run("PENNY", "v7", h)
    assert hasattr(res, "total_return"), "Result should have total_return"
    assert res.total_return > -1.0, "Should not lose more than 100%"


@pytest.mark.asyncio
async def test_expensive_stock():
    """Should handle expensive stocks ($5000+)."""
    h = sim(5000, 252, 0.15, 0.20, 8004)
    bt = BacktesterV7(initial_capital=10000)
    res = await bt.run("EXPENSIVE", "v7", h)
    assert hasattr(res, "total_return"), "Result should have total_return"
    assert isinstance(res.total_return, (int, float)), "total_return should be numeric"


@pytest.mark.asyncio
async def test_zero_volume():
    """Should work even with zero volume data."""
    h = [
        {"date": datetime(2025, 1, 1) + timedelta(days=i), "price": 100 * math.exp(0.15 / 252 * i), "volume": 0}
        for i in range(252)
    ]
    bt = BacktesterV7(initial_capital=10000)
    res = await bt.run("NOVOL", "v7", h)
    assert hasattr(res, "total_return"), "Result should have total_return"


# ═══════════════════════════════════════════════════════
# CONSISTENCY TESTS
# ═══════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_capital_conservation():
    """Final capital should match equity curve last value."""
    h = sim(100, 252, 0.20, 0.30, 9001)
    bt = BacktesterV7(initial_capital=10000)
    res = await bt.run("CC", "v7", h)
    final = 10000 * (1 + res.total_return)
    if len(res.equity_curve) > 0:
        eq_final = res.equity_curve[-1]
        diff = abs(final - eq_final) / max(final, 1)
        assert diff < 0.01, f"Capital mismatch: computed={final:.0f} vs equity={eq_final:.0f} ({diff:.1%})"


@pytest.mark.asyncio
async def test_no_negative_capital():
    """Capital should never go negative during backtest."""
    h = sim(100, 252, -0.50, 0.50, 9002, 0.05, 0.10)
    bt = BacktesterV7(initial_capital=10000)
    res = await bt.run("NEG", "v7", h)
    neg_eq = [e for e in res.equity_curve if e < 0]
    assert len(neg_eq) == 0, f"{len(neg_eq)} negative equity points found, min={min(res.equity_curve):.0f}"


@pytest.mark.asyncio
async def test_max_drawdown_accuracy():
    """Reported max drawdown should match equity curve."""
    h = sim(100, 252, 0.10, 0.35, 9003)
    bt = BacktesterV7(initial_capital=10000)
    res = await bt.run("DD", "v7", h)

    # Compute DD from equity curve
    peak = res.equity_curve[0]
    computed_dd = 0
    for eq in res.equity_curve:
        peak = max(peak, eq)
        dd = (eq - peak) / peak if peak > 0 else 0
        computed_dd = min(computed_dd, dd)

    diff = abs(res.max_drawdown - computed_dd)
    assert diff < 0.01, (
        f"DD mismatch: reported={res.max_drawdown:+.1%} vs computed={computed_dd:+.1%} (diff={diff:.4f})"
    )
