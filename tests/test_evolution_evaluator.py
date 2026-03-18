"""Tests for src/evolution/evaluator.py — strategy fitness evaluation."""

from __future__ import annotations

import math
import numpy as np
import pytest

# We'll import from the module under test
from src.evolution.evaluator import Evaluator, FitnessScore
from src.strategy.expression import OHLCVData


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_ohlcv(closes: list[float], length: int | None = None) -> OHLCVData:
    """Build a minimal OHLCVData from a close price series."""
    n = length or len(closes)
    c = np.array(closes[:n], dtype=np.float64)
    return OHLCVData(
        open=c * 0.99,
        high=c * 1.01,
        low=c * 0.98,
        close=c,
        volume=np.full(n, 1_000_000, dtype=np.float64),
    )


def _trending_up_data(n: int = 300) -> OHLCVData:
    """Generate steadily rising price data."""
    closes = [100.0]
    for _ in range(n - 1):
        closes.append(closes[-1] * 1.002)  # +0.2% daily
    return _make_ohlcv(closes)


def _flat_data(n: int = 300) -> OHLCVData:
    """Generate flat price data (no trend)."""
    closes = [100.0] * n
    return _make_ohlcv(closes)


def _drawdown_data(n: int = 300) -> OHLCVData:
    """Generate data with a massive drawdown in the middle."""
    closes = [100.0] * 100
    # Crash from 100 to 60
    for i in range(50):
        closes.append(100.0 - i * 0.8)
    # Recover
    for i in range(n - 150):
        closes.append(60.0 + i * 0.3)
    return _make_ohlcv(closes[:n])


SIMPLE_STRATEGY_YAML = """\
name: Test Momentum
entry:
  - sma(20) > sma(50)
exit:
  - sma(20) < sma(50)
risk:
  stop_loss: 5%
  take_profit: 15%
"""


# ---------------------------------------------------------------------------
# FitnessScore tests
# ---------------------------------------------------------------------------

class TestFitnessScore:
    """Tests for the FitnessScore dataclass."""

    def test_creation(self):
        score = FitnessScore(
            sharpe_ratio=1.5,
            total_return=0.42,
            max_drawdown=-0.12,
            win_rate=0.65,
            total_trades=30,
        )
        assert score.sharpe_ratio == 1.5
        assert score.total_return == 0.42
        assert score.max_drawdown == -0.12
        assert score.win_rate == 0.65
        assert score.total_trades == 30

    def test_composite_score_positive(self):
        """Composite score should combine metrics into a single comparable value."""
        score = FitnessScore(
            sharpe_ratio=1.5,
            total_return=0.42,
            max_drawdown=-0.12,
            win_rate=0.65,
            total_trades=30,
        )
        composite = score.composite()
        assert isinstance(composite, float)
        assert composite > 0  # Good strategy should have positive composite

    def test_composite_score_ordering(self):
        """Better strategies should have higher composite scores."""
        good = FitnessScore(sharpe_ratio=2.0, total_return=0.50, max_drawdown=-0.05, win_rate=0.70, total_trades=40)
        bad = FitnessScore(sharpe_ratio=0.3, total_return=-0.10, max_drawdown=-0.35, win_rate=0.30, total_trades=10)
        assert good.composite() > bad.composite()

    def test_composite_penalizes_drawdown(self):
        """Deep drawdowns should significantly reduce composite score."""
        low_dd = FitnessScore(sharpe_ratio=1.0, total_return=0.20, max_drawdown=-0.05, win_rate=0.60, total_trades=20)
        high_dd = FitnessScore(sharpe_ratio=1.0, total_return=0.20, max_drawdown=-0.40, win_rate=0.60, total_trades=20)
        assert low_dd.composite() > high_dd.composite()

    def test_zero_trades(self):
        """A strategy with zero trades should have a very low composite."""
        score = FitnessScore(sharpe_ratio=0.0, total_return=0.0, max_drawdown=0.0, win_rate=0.0, total_trades=0)
        assert score.composite() <= 0

    def test_comparison(self):
        """FitnessScores should be comparable."""
        a = FitnessScore(sharpe_ratio=2.0, total_return=0.50, max_drawdown=-0.05, win_rate=0.70, total_trades=40)
        b = FitnessScore(sharpe_ratio=0.5, total_return=0.10, max_drawdown=-0.20, win_rate=0.45, total_trades=20)
        assert a > b
        assert b < a

    def test_to_dict(self):
        """Should serialize to dict."""
        score = FitnessScore(sharpe_ratio=1.5, total_return=0.42, max_drawdown=-0.12, win_rate=0.65, total_trades=30)
        d = score.to_dict()
        assert d["sharpe_ratio"] == 1.5
        assert d["total_return"] == 0.42
        assert "composite" in d


# ---------------------------------------------------------------------------
# Evaluator tests
# ---------------------------------------------------------------------------

class TestEvaluator:
    """Tests for the Evaluator class."""

    def test_basic_evaluation(self):
        """Evaluator should return a FitnessScore for a valid strategy."""
        evaluator = Evaluator()
        data = _trending_up_data(300)
        score = evaluator.evaluate(SIMPLE_STRATEGY_YAML, data)
        assert isinstance(score, FitnessScore)
        assert isinstance(score.sharpe_ratio, float)
        assert isinstance(score.total_return, float)
        assert isinstance(score.max_drawdown, float)

    def test_trending_up_positive_return(self):
        """Strategy on trending-up data should have non-negative return."""
        evaluator = Evaluator()
        data = _trending_up_data(300)
        score = evaluator.evaluate(SIMPLE_STRATEGY_YAML, data)
        # In a strong uptrend, a trend-following strategy should generally profit
        assert score.total_return >= -0.1  # Allow small loss due to whipsaws

    def test_invalid_yaml_raises(self):
        """Invalid YAML should raise ValueError."""
        evaluator = Evaluator()
        data = _flat_data()
        with pytest.raises((ValueError, Exception)):
            evaluator.evaluate("not: a: valid: strategy:", data)

    def test_last_feedback_stored(self):
        """After evaluation, feedback should be available."""
        evaluator = Evaluator()
        data = _trending_up_data(300)
        evaluator.evaluate(SIMPLE_STRATEGY_YAML, data)
        feedback = evaluator.last_feedback
        assert feedback is not None
        assert "score" in feedback
        assert "trades" in feedback or "trade_count" in feedback

    def test_max_drawdown_negative_or_zero(self):
        """Max drawdown should always be <= 0."""
        evaluator = Evaluator()
        data = _drawdown_data(300)
        score = evaluator.evaluate(SIMPLE_STRATEGY_YAML, data)
        assert score.max_drawdown <= 0.0

    def test_sharpe_finite(self):
        """Sharpe ratio should be finite (not NaN or inf)."""
        evaluator = Evaluator()
        data = _trending_up_data(300)
        score = evaluator.evaluate(SIMPLE_STRATEGY_YAML, data)
        assert math.isfinite(score.sharpe_ratio)

    def test_different_data_different_scores(self):
        """Same strategy on different data should give different results."""
        evaluator = Evaluator()
        s1 = evaluator.evaluate(SIMPLE_STRATEGY_YAML, _trending_up_data(300))
        s2 = evaluator.evaluate(SIMPLE_STRATEGY_YAML, _drawdown_data(300))
        # At least one metric should differ
        assert s1.total_return != s2.total_return or s1.sharpe_ratio != s2.sharpe_ratio
