"""Tests for factor correlation analysis and turnover penalty.

Covers:
  - Pearson correlation calculation
  - Identical factors (correlation = 1.0)
  - Uncorrelated random data
  - Redundant pair detection
  - Pruning logic
  - Cluster building
  - IC-based representative selection
  - save_correlation_matrix JSON output
  - Turnover penalty in compute_fitness
  - Turnover penalty boundary values
"""

import json
import math
import os
import random
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from src.evolution.factor_correlation import (
    ClusterInfo,
    FactorCorrelationAnalyzer,
    _pearson_correlation,
)
from src.evolution.auto_evolve import compute_fitness


# ────────────────── Helpers ──────────────────


def _make_fake_registry(factors: Dict[str, callable]):
    """Create a mock FactorRegistry with given factors."""
    from dataclasses import dataclass

    @dataclass
    class FakeMeta:
        name: str
        compute_fn: callable

    class FakeRegistry:
        def __init__(self, fdict):
            self.factors = {
                name: FakeMeta(name=name, compute_fn=fn)
                for name, fn in fdict.items()
            }

        def list_factors(self):
            return list(self.factors.keys())

    return FakeRegistry(factors)


def _make_synthetic_data(
    n_stocks: int = 10,
    n_days: int = 150,
    seed: int = 42,
) -> Dict[str, Dict[str, list]]:
    """Generate synthetic stock data for testing."""
    rng = random.Random(seed)
    data = {}
    for i in range(n_stocks):
        code = f"stock_{i:03d}"
        price = 10.0
        closes, highs, lows, volumes, opens = [], [], [], [], []
        for d in range(n_days):
            ret = 0.001 + 0.02 * rng.gauss(0, 1)
            o = price
            c = price * (1 + ret)
            h = max(o, c) * (1 + rng.uniform(0, 0.01))
            lo = min(o, c) * (1 - rng.uniform(0, 0.01))
            vol = rng.randint(1_000_000, 50_000_000)
            opens.append(o)
            closes.append(c)
            highs.append(h)
            lows.append(lo)
            volumes.append(vol)
            price = c
        data[code] = {
            "close": closes,
            "open": opens,
            "high": highs,
            "low": lows,
            "volume": volumes,
        }
    return data


# ────────────────── Pearson Correlation Tests ──────────────────


class TestPearsonCorrelation:
    """Tests for the _pearson_correlation utility function."""

    def test_identical_vectors(self):
        """Identical vectors should have correlation 1.0."""
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert abs(_pearson_correlation(x, x) - 1.0) < 1e-10

    def test_perfectly_negative(self):
        """Perfectly negatively correlated vectors → -1.0."""
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [5.0, 4.0, 3.0, 2.0, 1.0]
        assert abs(_pearson_correlation(x, y) - (-1.0)) < 1e-10

    def test_uncorrelated_random(self):
        """Large random vectors should have near-zero correlation."""
        rng = random.Random(123)
        x = [rng.gauss(0, 1) for _ in range(5000)]
        rng2 = random.Random(456)
        y = [rng2.gauss(0, 1) for _ in range(5000)]
        corr = _pearson_correlation(x, y)
        assert abs(corr) < 0.05, f"Expected near-zero corr, got {corr}"

    def test_empty_vectors(self):
        """Empty vectors should return 0.0."""
        assert _pearson_correlation([], []) == 0.0

    def test_constant_vector(self):
        """A constant vector has zero variance → correlation should be 0.0."""
        x = [3.0, 3.0, 3.0, 3.0]
        y = [1.0, 2.0, 3.0, 4.0]
        assert _pearson_correlation(x, y) == 0.0

    def test_length_mismatch(self):
        """Mismatched vector lengths → 0.0."""
        assert _pearson_correlation([1.0, 2.0], [1.0]) == 0.0


# ────────────────── Factor Correlation Analyzer Tests ──────────────────


class TestFactorCorrelationAnalyzer:
    """Tests for the FactorCorrelationAnalyzer class."""

    def test_identical_factors_corr_one(self):
        """Two identical factor functions should yield correlation ~1.0."""
        data = _make_synthetic_data(n_stocks=10, n_days=100)

        def momentum(closes, highs, lows, volumes, idx):
            if idx < 10:
                return 0.5
            return max(0.0, min(1.0, (closes[idx] - closes[idx - 10]) / closes[idx - 10] + 0.5))

        # Both factors are identical
        registry = _make_fake_registry({
            "momentum_a": momentum,
            "momentum_b": momentum,
        })

        analyzer = FactorCorrelationAnalyzer(data, registry, correlation_threshold=0.7)
        analyzer.compute(sample_stocks=10, sample_dates=50)

        corr = analyzer.correlation_matrix["momentum_a"]["momentum_b"]
        assert abs(corr - 1.0) < 1e-6, f"Identical factors should have corr=1.0, got {corr}"

    def test_uncorrelated_factors(self):
        """Completely different factor functions should have low correlation."""
        data = _make_synthetic_data(n_stocks=20, n_days=100, seed=99)

        def factor_price_level(closes, highs, lows, volumes, idx):
            # Depends on price
            return max(0.0, min(1.0, closes[idx] / 20.0))

        def factor_volume_spike(closes, highs, lows, volumes, idx):
            # Depends on volume only, independent of price
            if idx < 5:
                return 0.5
            avg_vol = sum(volumes[idx-5:idx]) / 5
            return max(0.0, min(1.0, volumes[idx] / (avg_vol + 1) / 2.0))

        registry = _make_fake_registry({
            "price_level": factor_price_level,
            "volume_spike": factor_volume_spike,
        })

        analyzer = FactorCorrelationAnalyzer(data, registry, correlation_threshold=0.7)
        analyzer.compute(sample_stocks=20, sample_dates=60)

        corr = analyzer.correlation_matrix["price_level"]["volume_spike"]
        assert abs(corr) < 0.7, f"Expected low correlation, got {corr}"

    def test_redundant_pair_detection(self):
        """Identical factors should be detected as a redundant pair."""
        data = _make_synthetic_data(n_stocks=10, n_days=100)

        def same_factor(closes, highs, lows, volumes, idx):
            if idx < 5:
                return 0.5
            return max(0.0, min(1.0, (closes[idx] - closes[idx - 5]) / closes[idx - 5] + 0.5))

        registry = _make_fake_registry({
            "alpha": same_factor,
            "beta": same_factor,
        })

        analyzer = FactorCorrelationAnalyzer(data, registry, correlation_threshold=0.7)
        analyzer.compute(sample_stocks=10, sample_dates=50)

        pairs = analyzer.get_redundant_pairs()
        assert len(pairs) >= 1, "Should detect at least one redundant pair"
        f1, f2, corr = pairs[0]
        assert {f1, f2} == {"alpha", "beta"}
        assert abs(corr) > 0.7

    def test_pruning_removes_redundant(self):
        """get_pruned_factor_list should remove redundant factors."""
        data = _make_synthetic_data(n_stocks=10, n_days=100)

        def same_factor(closes, highs, lows, volumes, idx):
            if idx < 5:
                return 0.5
            return max(0.0, min(1.0, (closes[idx] - closes[idx - 5]) / closes[idx - 5] + 0.5))

        def different_factor(closes, highs, lows, volumes, idx):
            # Random-ish based on volumes
            return max(0.0, min(1.0, (volumes[idx] % 1000) / 1000.0))

        registry = _make_fake_registry({
            "dup_a": same_factor,
            "dup_b": same_factor,
            "unique": different_factor,
        })

        analyzer = FactorCorrelationAnalyzer(data, registry, correlation_threshold=0.7)
        analyzer.compute(sample_stocks=10, sample_dates=50)

        pruned = analyzer.get_pruned_factor_list(["dup_a", "dup_b", "unique"])
        assert "unique" in pruned, "Non-redundant factor should stay"
        # One of the dups should be removed
        assert len(pruned) < 3, f"Expected pruning, got {pruned}"
        # At least one dup should remain
        assert "dup_a" in pruned or "dup_b" in pruned

    def test_pruning_with_ic_scores(self):
        """When IC scores are provided, the higher-IC factor should be kept."""
        data = _make_synthetic_data(n_stocks=10, n_days=100)

        def same_factor(closes, highs, lows, volumes, idx):
            if idx < 5:
                return 0.5
            return max(0.0, min(1.0, (closes[idx] - closes[idx - 5]) / closes[idx - 5] + 0.5))

        registry = _make_fake_registry({
            "low_ic": same_factor,
            "high_ic": same_factor,
        })

        # high_ic has better IC
        analyzer = FactorCorrelationAnalyzer(
            data, registry,
            ic_scores={"low_ic": 0.01, "high_ic": 0.05},
            correlation_threshold=0.7,
        )
        analyzer.compute(sample_stocks=10, sample_dates=50)

        pruned = analyzer.get_pruned_factor_list(["low_ic", "high_ic"])
        assert "high_ic" in pruned, f"Higher-IC factor should be kept, got {pruned}"
        assert len(pruned) == 1, f"Should prune to 1 factor, got {pruned}"

    def test_save_correlation_matrix(self, tmp_path):
        """save_correlation_matrix should write valid JSON with expected keys."""
        data = _make_synthetic_data(n_stocks=5, n_days=80)

        def f1(closes, highs, lows, volumes, idx):
            return 0.5

        def f2(closes, highs, lows, volumes, idx):
            return 0.3

        registry = _make_fake_registry({"factor_a": f1, "factor_b": f2})

        analyzer = FactorCorrelationAnalyzer(data, registry, correlation_threshold=0.7)
        analyzer.compute(sample_stocks=5, sample_dates=30)

        out_path = str(tmp_path / "corr.json")
        analyzer.save_correlation_matrix(out_path)

        assert os.path.exists(out_path)
        with open(out_path, "r", encoding="utf-8") as f:
            result = json.load(f)

        assert "correlation_matrix" in result
        assert "redundant_pairs" in result
        assert "pruned_factor_list" in result
        assert "clusters" in result
        assert "threshold" in result
        assert result["total_factors"] == 2

    def test_no_factors(self):
        """Empty registry should not crash."""
        data = _make_synthetic_data(n_stocks=5, n_days=80)
        registry = _make_fake_registry({})

        analyzer = FactorCorrelationAnalyzer(data, registry)
        analyzer.compute()

        assert analyzer.get_redundant_pairs() == []
        pruned = analyzer.get_pruned_factor_list([])
        assert pruned == []

    def test_compute_required_before_access(self):
        """Accessing results before compute() should raise RuntimeError."""
        data = _make_synthetic_data(n_stocks=5, n_days=80)
        registry = _make_fake_registry({"x": lambda c, h, l, v, i: 0.5})

        analyzer = FactorCorrelationAnalyzer(data, registry)

        with pytest.raises(RuntimeError, match="compute"):
            analyzer.get_redundant_pairs()

        with pytest.raises(RuntimeError, match="compute"):
            analyzer.get_pruned_factor_list(["x"])

        with pytest.raises(RuntimeError, match="compute"):
            analyzer.save_correlation_matrix("/tmp/test.json")

    def test_symmetric_matrix(self):
        """Correlation matrix should be symmetric: corr(A,B) == corr(B,A)."""
        data = _make_synthetic_data(n_stocks=10, n_days=100)

        def f1(closes, highs, lows, volumes, idx):
            return max(0.0, min(1.0, closes[idx] / 15.0))

        def f2(closes, highs, lows, volumes, idx):
            if idx < 10:
                return 0.5
            return max(0.0, min(1.0, sum(closes[idx-5:idx]) / (5 * closes[idx])))

        def f3(closes, highs, lows, volumes, idx):
            return max(0.0, min(1.0, volumes[idx] / 30_000_000))

        registry = _make_fake_registry({"f1": f1, "f2": f2, "f3": f3})
        analyzer = FactorCorrelationAnalyzer(data, registry)
        analyzer.compute(sample_stocks=10, sample_dates=50)

        for a in ["f1", "f2", "f3"]:
            for b in ["f1", "f2", "f3"]:
                assert abs(
                    analyzer.correlation_matrix[a][b]
                    - analyzer.correlation_matrix[b][a]
                ) < 1e-10, f"Matrix not symmetric for ({a}, {b})"


# ────────────────── Turnover Penalty Tests ──────────────────


class TestTurnoverPenalty:
    """Tests for the turnover penalty in compute_fitness."""

    def test_no_turnover_no_penalty(self):
        """Zero turnover should not reduce fitness."""
        base = compute_fitness(
            annual_return=20.0,
            max_drawdown=10.0,
            win_rate=60.0,
            sharpe=1.5,
            total_trades=100,
            avg_turnover=0.0,
        )
        # Same calculation without explicit turnover should give same result
        base_default = compute_fitness(
            annual_return=20.0,
            max_drawdown=10.0,
            win_rate=60.0,
            sharpe=1.5,
            total_trades=100,
        )
        assert abs(base - base_default) < 1e-10

    def test_moderate_turnover_penalty(self):
        """Turnover between 0.5 and 0.8 should multiply fitness by 0.95."""
        no_penalty = compute_fitness(
            annual_return=20.0,
            max_drawdown=10.0,
            win_rate=60.0,
            sharpe=1.5,
            total_trades=100,
            avg_turnover=0.0,
        )
        with_moderate = compute_fitness(
            annual_return=20.0,
            max_drawdown=10.0,
            win_rate=60.0,
            sharpe=1.5,
            total_trades=100,
            avg_turnover=0.6,
        )
        assert abs(with_moderate - no_penalty * 0.95) < 1e-10

    def test_high_turnover_penalty(self):
        """Turnover above 0.8 should multiply fitness by 0.85."""
        no_penalty = compute_fitness(
            annual_return=20.0,
            max_drawdown=10.0,
            win_rate=60.0,
            sharpe=1.5,
            total_trades=100,
            avg_turnover=0.0,
        )
        with_high = compute_fitness(
            annual_return=20.0,
            max_drawdown=10.0,
            win_rate=60.0,
            sharpe=1.5,
            total_trades=100,
            avg_turnover=0.9,
        )
        assert abs(with_high - no_penalty * 0.85) < 1e-10

    def test_turnover_boundary_at_0_5(self):
        """Turnover exactly at 0.5 should NOT trigger the penalty (> not >=)."""
        no_penalty = compute_fitness(
            annual_return=20.0,
            max_drawdown=10.0,
            win_rate=60.0,
            sharpe=1.5,
            total_trades=100,
            avg_turnover=0.0,
        )
        at_boundary = compute_fitness(
            annual_return=20.0,
            max_drawdown=10.0,
            win_rate=60.0,
            sharpe=1.5,
            total_trades=100,
            avg_turnover=0.5,
        )
        assert abs(at_boundary - no_penalty) < 1e-10

    def test_turnover_boundary_at_0_8(self):
        """Turnover exactly at 0.8 should trigger moderate penalty (0.95), not severe (0.85)."""
        no_penalty = compute_fitness(
            annual_return=20.0,
            max_drawdown=10.0,
            win_rate=60.0,
            sharpe=1.5,
            total_trades=100,
            avg_turnover=0.0,
        )
        at_boundary = compute_fitness(
            annual_return=20.0,
            max_drawdown=10.0,
            win_rate=60.0,
            sharpe=1.5,
            total_trades=100,
            avg_turnover=0.8,
        )
        # 0.8 is not > 0.8, so it should be the moderate penalty (> 0.5)
        assert abs(at_boundary - no_penalty * 0.95) < 1e-10

    def test_high_turnover_reduces_more(self):
        """Higher turnover should always result in lower or equal fitness."""
        low = compute_fitness(20.0, 10.0, 60.0, 1.5, 100, avg_turnover=0.3)
        moderate = compute_fitness(20.0, 10.0, 60.0, 1.5, 100, avg_turnover=0.6)
        high = compute_fitness(20.0, 10.0, 60.0, 1.5, 100, avg_turnover=0.9)
        assert low >= moderate >= high
        assert low > high  # strict inequality
