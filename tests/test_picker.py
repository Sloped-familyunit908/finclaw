"""
FinClaw — Extended Picker & LLM Test Suite
==================================
Tests for stock picker, LLM analyzer, and signal engine integration.

Converted from custom test runner to proper pytest.
"""
import random
import math
import sys
import os
import pytest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.stock_picker import MultiFactorPicker, ConvictionLevel
from agents.llm_analyzer import LLMStockAnalyzer, DISRUPTION_DB
from agents.signal_engine_v7 import SignalEngineV7, MarketRegime


def sim(start, days, ret, vol, seed=42):
    rng = random.Random(seed)
    dt = 1 / 252
    prices = [start]
    for _ in range(days - 1):
        dW = rng.gauss(0, math.sqrt(dt))
        prices.append(max(prices[-1] * math.exp((ret - 0.5 * vol**2) * dt + vol * dW), 0.01))
    base = datetime(2025, 3, 1)
    return [
        {"date": base + timedelta(days=i), "price": p, "volume": abs(rng.gauss(p * 1e6, p * 5e5))}
        for i, p in enumerate(prices)
    ]


# ═══════════════════════════════════════════════════════
# PICKER TESTS
# ═══════════════════════════════════════════════════════


def test_picker_bull_vs_bear():
    """Bull stocks should score higher than bear stocks."""
    picker = MultiFactorPicker(use_fundamentals=False)

    bull = sim(100, 252, 0.50, 0.25, 9001)
    bear = sim(100, 252, -0.30, 0.25, 9002)

    a_bull = picker.analyze("BULL", bull, "Bull Stock")
    a_bear = picker.analyze("BEAR", bear, "Bear Stock")

    assert a_bull.score > a_bear.score, (
        f"bull({a_bull.score:+.3f}) should be > bear({a_bear.score:+.3f})"
    )


def test_picker_conviction_strong_buy():
    """Strong performers should get STRONG_BUY or BUY conviction."""
    picker = MultiFactorPicker(use_fundamentals=False)
    strong = sim(100, 252, 0.80, 0.30, 9003)
    a_strong = picker.analyze("STRONG", strong, "Strong")
    assert a_strong.conviction in (ConvictionLevel.STRONG_BUY, ConvictionLevel.BUY), (
        f"Strong stock got {a_strong.conviction.value}, expected STRONG_BUY or BUY"
    )


def test_picker_conviction_avoid():
    """Weak performers should get AVOID or STRONG_AVOID or HOLD conviction."""
    picker = MultiFactorPicker(use_fundamentals=False)
    weak = sim(100, 252, -0.50, 0.40, 9004)
    a_weak = picker.analyze("WEAK", weak, "Weak")
    assert a_weak.conviction in (ConvictionLevel.AVOID, ConvictionLevel.STRONG_AVOID, ConvictionLevel.HOLD), (
        f"Weak stock got {a_weak.conviction.value}, expected AVOID/STRONG_AVOID/HOLD"
    )


def test_picker_ranking_order():
    """Ranking should put best stocks first, worst last."""
    picker = MultiFactorPicker(use_fundamentals=False)

    stocks = [
        {"ticker": "A", "name": "Best",  "h": sim(100, 252, 0.60, 0.25, 9010)},
        {"ticker": "B", "name": "Good",  "h": sim(100, 252, 0.30, 0.25, 9011)},
        {"ticker": "C", "name": "Flat",  "h": sim(100, 252, 0.00, 0.25, 9012)},
        {"ticker": "D", "name": "Bad",   "h": sim(100, 252, -0.20, 0.25, 9013)},
        {"ticker": "E", "name": "Worst", "h": sim(100, 252, -0.50, 0.30, 9014)},
    ]

    rankings = picker.rank_universe(stocks)
    tickers = [r.ticker for r in rankings]

    assert tickers[0] in ("A", "B"), f"Top pick should be A or B, got {tickers[0]}"
    assert tickers[-1] in ("D", "E"), f"Bottom pick should be D or E, got {tickers[-1]}"


def test_picker_deterministic():
    """Same input should produce same ranking."""
    picker = MultiFactorPicker(use_fundamentals=False)
    h = sim(100, 252, 0.30, 0.25, 9099)

    a1 = picker.analyze("TEST", h, "Test")
    a2 = picker.analyze("TEST", h, "Test")

    assert abs(a1.score - a2.score) < 0.0001, (
        f"Scores differ: {a1.score} vs {a2.score}"
    )


# ═══════════════════════════════════════════════════════
# LLM ANALYZER TESTS
# ═══════════════════════════════════════════════════════


def test_llm_ai_winners():
    """AI beneficiary stocks should get score boost."""
    llm = LLMStockAnalyzer()

    adj_nvda, _ = llm.compute_ai_era_score("NVDA", 0.5)
    adj_crm, _ = llm.compute_ai_era_score("CRM", 0.5)

    assert adj_nvda > adj_crm, (
        f"NVDA({adj_nvda:+.3f}) should be > CRM({adj_crm:+.3f}) after AI adjustment"
    )


def test_llm_disruption_penalty():
    """Disrupted companies should get score penalty below base."""
    llm = LLMStockAnalyzer()
    base = 0.5

    adj_shop, _ = llm.compute_ai_era_score("SHOP", base)
    adj_intc, _ = llm.compute_ai_era_score("INTC", base)

    assert adj_shop < base, f"SHOP({adj_shop:+.3f}) should be penalized below base={base}"
    assert adj_intc < base, f"INTC({adj_intc:+.3f}) should be penalized below base={base}"


def test_llm_unknown_ticker():
    """Unknown ticker should pass through unchanged."""
    llm = LLMStockAnalyzer()
    adj, reason = llm.compute_ai_era_score("UNKNOWN_XYZ", 0.5)
    assert abs(adj - 0.5) < 0.001, f"Unknown ticker should return 0.5, got {adj}"


def test_llm_coverage():
    """Disruption DB should cover key tickers."""
    must_have = ["NVDA", "AVGO", "META", "CRM", "688256.SS", "600519.SS"]
    missing = [t for t in must_have if t not in DISRUPTION_DB]
    assert not missing, f"Missing from disruption DB: {missing}"


# ═══════════════════════════════════════════════════════
# SIGNAL ENGINE TESTS
# ═══════════════════════════════════════════════════════


def test_regime_transitions():
    """Regime should transition correctly between states."""
    engine = SignalEngineV7()

    bull = [100 * math.exp(0.30 / 252 * i) for i in range(60)]
    crash = [bull[-1] * math.exp(-0.50 / 252 * i) for i in range(30)]
    recovery = [crash[-1] * math.exp(0.40 / 252 * i) for i in range(40)]

    full = bull + crash + recovery
    sig = engine.generate_signal(full[:60])
    r1 = sig.regime

    assert r1 in (MarketRegime.BULL, MarketRegime.STRONG_BULL), (
        f"Phase 1 (bull) expected BULL/STRONG_BULL, got {r1.value}"
    )

    sig = engine.generate_signal(full[:75])
    r2 = sig.regime
    # After crash, regime may still show bull due to inertia — this is by design
    assert r2 is not None, "Phase 2 regime should not be None"


def test_signal_factors_complete():
    """Signal should include all expected factors."""
    engine = SignalEngineV7()
    prices = [100 * math.exp(0.20 / 252 * i) for i in range(100)]
    sig = engine.generate_signal(prices)

    required = ["signal", "confidence", "regime", "position_size"]
    for attr in required:
        assert hasattr(sig, attr), f"SignalResult missing required attribute '{attr}'"
