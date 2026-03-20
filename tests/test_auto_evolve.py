"""Tests for the automatic strategy evolution engine (auto_evolve.py).

Covers: StrategyDNA, mutation, crossover, indicators, scoring,
        fitness, evaluate, run_generation, save/load, and edge cases.
"""

import json
import math
import os
import random
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.evolution.auto_evolve import (
    AutoEvolver,
    EvolutionResult,
    StrategyDNA,
    _PARAM_RANGES,
    compute_fitness,
    compute_linear_regression,
    compute_rsi,
    compute_volume_ratio,
    score_stock,
)


# ────────────────── Helpers ──────────────────


def _make_synthetic_csv(
    path: Path,
    code: str = "test_001",
    days: int = 250,
    start_price: float = 10.0,
    trend: float = 0.001,
    seed: int = 42,
):
    """Generate a synthetic stock CSV file for testing."""
    rng = random.Random(seed)
    fp = path / f"{code}.csv"
    lines = ["date,code,open,high,low,close,volume,amount,turn"]
    price = start_price
    for d in range(days):
        date_str = f"2024-{(d // 30) + 1:02d}-{(d % 30) + 1:02d}"
        ret = trend + 0.02 * rng.gauss(0, 1)
        o = price
        c = price * (1 + ret)
        h = max(o, c) * (1 + rng.uniform(0, 0.01))
        lo = min(o, c) * (1 - rng.uniform(0, 0.01))
        vol = rng.randint(1_000_000, 50_000_000)
        amt = vol * c
        lines.append(
            f"{date_str},{code},{o:.4f},{h:.4f},{lo:.4f},{c:.4f},{vol},{amt:.2f},1.0"
        )
        price = c
    fp.write_text("\n".join(lines), encoding="utf-8")
    return fp


def _make_data_dir(tmp_path: Path, n_stocks: int = 5, days: int = 250) -> Path:
    """Create a temp data dir with N synthetic stocks."""
    data_dir = tmp_path / "test_shares"
    data_dir.mkdir()
    for i in range(n_stocks):
        _make_synthetic_csv(data_dir, code=f"stock_{i:03d}", days=days, seed=42 + i)
    return data_dir


# ────────────────── StrategyDNA tests ──────────────────


class TestStrategyDNA:
    def test_defaults(self):
        dna = StrategyDNA()
        assert dna.min_score == 6
        assert dna.hold_days == 3
        assert dna.stop_loss_pct == 2.0

    def test_to_dict_roundtrip(self):
        dna = StrategyDNA(min_score=8, rsi_buy_threshold=30.0)
        d = dna.to_dict()
        restored = StrategyDNA.from_dict(d)
        assert restored.min_score == 8
        assert restored.rsi_buy_threshold == 30.0
        assert restored.to_dict() == d

    def test_from_dict_ignores_extra_keys(self):
        d = StrategyDNA().to_dict()
        d["unknown_param"] = 999
        dna = StrategyDNA.from_dict(d)
        assert not hasattr(dna, "unknown_param")

    def test_weights_sum_approximately_one(self):
        dna = StrategyDNA()
        total = dna.w_momentum + dna.w_mean_reversion + dna.w_volume + dna.w_trend + dna.w_pattern
        assert abs(total - 1.0) < 0.01


# ────────────────── Mutation tests ──────────────────


class TestMutation:
    def test_mutation_produces_valid_params(self):
        """Mutated DNA should have all params within valid ranges."""
        evolver = AutoEvolver(data_dir=".", seed=42)
        dna = StrategyDNA()

        for _ in range(100):
            mutated = evolver.mutate(dna)
            for param, (lo, hi, is_int) in _PARAM_RANGES.items():
                val = getattr(mutated, param)
                assert lo <= val <= hi, f"{param}={val} out of range [{lo}, {hi}]"
                if is_int:
                    assert isinstance(val, int), f"{param} should be int, got {type(val)}"

    def test_mutation_changes_something(self):
        """Over many mutations, at least some parameters should change."""
        evolver = AutoEvolver(data_dir=".", mutation_rate=1.0, seed=42)
        dna = StrategyDNA()
        mutated = evolver.mutate(dna)
        # With mutation_rate=1.0, all params should be attempted
        d1 = dna.to_dict()
        d2 = mutated.to_dict()
        changed = sum(1 for k in d1 if d1[k] != d2[k])
        assert changed > 0, "Mutation with rate 1.0 should change at least one param"

    def test_mutation_rate_zero_preserves_dna(self):
        """With mutation rate 0, DNA should be unchanged (except weight normalization)."""
        evolver = AutoEvolver(data_dir=".", mutation_rate=0.0, seed=42)
        dna = StrategyDNA()
        mutated = evolver.mutate(dna)
        # Non-weight params should be identical
        for param in _PARAM_RANGES:
            if not param.startswith("w_"):
                assert getattr(mutated, param) == getattr(dna, param), (
                    f"{param} changed with mutation_rate=0"
                )

    def test_mutation_normalizes_weights(self):
        """After mutation, weights should sum ≈ 1.0."""
        evolver = AutoEvolver(data_dir=".", mutation_rate=1.0, seed=123)
        dna = StrategyDNA()
        for _ in range(50):
            mutated = evolver.mutate(dna)
            w_sum = (
                mutated.w_momentum
                + mutated.w_mean_reversion
                + mutated.w_volume
                + mutated.w_trend
                + mutated.w_pattern
            )
            assert abs(w_sum - 1.0) < 0.01, f"Weights sum to {w_sum}, expected ≈1.0"


# ────────────────── Crossover tests ──────────────────


class TestCrossover:
    def test_crossover_preserves_parent_genes(self):
        """Child should only contain values from one of the two parents."""
        evolver = AutoEvolver(data_dir=".", seed=42)
        dna1 = StrategyDNA(min_score=3, hold_days=5, stop_loss_pct=1.0)
        dna2 = StrategyDNA(min_score=9, hold_days=15, stop_loss_pct=8.0)

        d1 = dna1.to_dict()
        d2 = dna2.to_dict()

        # Run many crossovers; each non-weight param should come from a parent
        for _ in range(50):
            child = evolver.crossover(dna1, dna2)
            dc = child.to_dict()
            for key in ["min_score", "hold_days", "stop_loss_pct", "rsi_buy_threshold"]:
                assert dc[key] in (d1[key], d2[key]), (
                    f"{key}={dc[key]} not from either parent ({d1[key]}, {d2[key]})"
                )

    def test_crossover_normalizes_weights(self):
        """After crossover, weights should sum ≈ 1.0."""
        evolver = AutoEvolver(data_dir=".", seed=42)
        dna1 = StrategyDNA()
        dna2 = StrategyDNA(w_momentum=0.5, w_trend=0.5, w_volume=0.0, w_mean_reversion=0.0, w_pattern=0.0)
        child = evolver.crossover(dna1, dna2)
        w_sum = child.w_momentum + child.w_mean_reversion + child.w_volume + child.w_trend + child.w_pattern
        assert abs(w_sum - 1.0) < 0.01


# ────────────────── Indicator tests ──────────────────


class TestIndicators:
    def test_rsi_range(self):
        """RSI values should be in [0, 100]."""
        prices = [100 + i * 0.5 + random.gauss(0, 1) for i in range(100)]
        rsi = compute_rsi(prices)
        valid = [v for v in rsi if not math.isnan(v)]
        assert len(valid) > 0
        for v in valid:
            assert 0 <= v <= 100, f"RSI {v} out of range"

    def test_rsi_uptrend(self):
        """RSI of a pure uptrend should be high."""
        prices = [100 + i * 2 for i in range(100)]
        rsi = compute_rsi(prices)
        # Last RSI should be near 100
        assert rsi[-1] > 80

    def test_rsi_downtrend(self):
        """RSI of a pure downtrend should be low."""
        prices = [200 - i * 1.5 for i in range(100)]
        rsi = compute_rsi(prices)
        assert rsi[-1] < 20

    def test_linear_regression_uptrend(self):
        """Perfect uptrend should have R² ≈ 1 and positive slope."""
        prices = [100 + i * 0.5 for i in range(50)]
        r2, slope = compute_linear_regression(prices, window=20)
        # Last values should show strong trend
        assert r2[-1] > 0.99
        assert slope[-1] > 0

    def test_volume_ratio(self):
        """Volume ratio should be ~1 for flat volume, >1 for spike."""
        volumes = [1_000_000] * 30
        volumes.append(3_000_000)  # spike
        ratios = compute_volume_ratio(volumes, period=20)
        assert ratios[-1] == pytest.approx(3.0, abs=0.01)


# ────────────────── Fitness tests ──────────────────


class TestFitness:
    def test_fitness_positive_for_good_strategy(self):
        f = compute_fitness(
            annual_return=25.0,
            max_drawdown=10.0,
            win_rate=60.0,
            sharpe=1.5,
        )
        assert f > 0

    def test_fitness_increases_with_better_return(self):
        f1 = compute_fitness(20.0, 10.0, 50.0, 1.0)
        f2 = compute_fitness(40.0, 10.0, 50.0, 1.0)
        assert f2 > f1

    def test_fitness_decreases_with_higher_drawdown(self):
        f1 = compute_fitness(20.0, 5.0, 50.0, 1.0)
        f2 = compute_fitness(20.0, 30.0, 50.0, 1.0)
        assert f1 > f2

    def test_fitness_negative_return_gives_negative_fitness(self):
        f = compute_fitness(-20.0, 30.0, 30.0, -1.0)
        assert f < 0

    def test_fitness_floor_drawdown_at_5(self):
        """Drawdown < 5 should be treated as 5 (floor)."""
        f1 = compute_fitness(20.0, 1.0, 50.0, 1.0)
        f2 = compute_fitness(20.0, 5.0, 50.0, 1.0)
        assert f1 == f2  # Both use denominator 5.0

    def test_fitness_zero_sharpe_no_bonus(self):
        """Sharpe=0 means bonus factor is 1.0 (no boost)."""
        f = compute_fitness(20.0, 10.0, 50.0, 0.0)
        expected = 20.0 * math.sqrt(50.0) / 10.0 * 1.0
        assert abs(f - expected) < 0.01


# ────────────────── Scoring tests ──────────────────


class TestScoring:
    def test_score_returns_0_to_10(self):
        rsi = [float("nan")] * 20 + [40.0] * 80
        r2 = [float("nan")] * 20 + [0.7] * 80
        slope = [float("nan")] * 20 + [1.0] * 80
        vol_ratio = [float("nan")] * 20 + [1.5] * 80
        closes = [100 + i * 0.5 for i in range(100)]
        dna = StrategyDNA()

        s = score_stock(50, rsi, r2, slope, vol_ratio, closes, dna)
        assert 0 <= s <= 10

    def test_score_nan_returns_zero(self):
        n = 50
        rsi = [float("nan")] * n
        r2 = [float("nan")] * n
        slope = [float("nan")] * n
        vol_ratio = [float("nan")] * n
        closes = [100.0] * n
        dna = StrategyDNA()

        assert score_stock(25, rsi, r2, slope, vol_ratio, closes, dna) == 0.0


# ────────────────── Evaluate tests ──────────────────


class TestEvaluate:
    def test_evaluate_on_synthetic_data(self, tmp_path):
        """Evaluate should return reasonable metrics on synthetic data."""
        data_dir = _make_data_dir(tmp_path, n_stocks=10, days=250)
        evolver = AutoEvolver(
            data_dir=str(data_dir),
            results_dir=str(tmp_path / "results"),
            seed=42,
        )
        data = evolver.load_data()
        assert len(data) == 10

        result = evolver.evaluate(StrategyDNA(), data)
        assert isinstance(result, EvolutionResult)
        assert result.max_drawdown >= 0
        assert 0 <= result.win_rate <= 100

    def test_evaluate_empty_data_returns_zeros(self):
        evolver = AutoEvolver(data_dir="nonexistent", seed=42)
        result = evolver.evaluate(StrategyDNA(), {})
        assert result.fitness == 0.0
        assert result.total_trades == 0

    def test_evaluate_result_to_dict_roundtrip(self, tmp_path):
        data_dir = _make_data_dir(tmp_path, n_stocks=3, days=100)
        evolver = AutoEvolver(
            data_dir=str(data_dir),
            results_dir=str(tmp_path / "results"),
            seed=42,
        )
        data = evolver.load_data()
        result = evolver.evaluate(StrategyDNA(), data)

        d = result.to_dict()
        assert "dna" in d
        assert "fitness" in d
        assert isinstance(d["dna"], dict)


# ────────────────── Load data tests ──────────────────


class TestLoadData:
    def test_loads_valid_csvs(self, tmp_path):
        data_dir = _make_data_dir(tmp_path, n_stocks=3, days=100)
        evolver = AutoEvolver(data_dir=str(data_dir), seed=42)
        data = evolver.load_data()
        assert len(data) == 3
        for code, sd in data.items():
            assert "close" in sd
            assert "open" in sd
            assert len(sd["close"]) >= 60

    def test_skips_short_csv(self, tmp_path):
        """Stocks with < 60 days should be skipped."""
        data_dir = tmp_path / "short"
        data_dir.mkdir()
        _make_synthetic_csv(data_dir, code="short_stock", days=30)
        evolver = AutoEvolver(data_dir=str(data_dir), seed=42)
        data = evolver.load_data()
        assert len(data) == 0

    def test_empty_dir_returns_empty(self, tmp_path):
        data_dir = tmp_path / "empty_dir"
        data_dir.mkdir()
        evolver = AutoEvolver(data_dir=str(data_dir), seed=42)
        data = evolver.load_data()
        assert data == {}


# ────────────────── Generation tests ──────────────────


class TestRunGeneration:
    def test_run_generation_returns_elite_count(self, tmp_path):
        data_dir = _make_data_dir(tmp_path, n_stocks=5, days=150)
        evolver = AutoEvolver(
            data_dir=str(data_dir),
            population_size=10,
            elite_count=3,
            results_dir=str(tmp_path / "results"),
            seed=42,
        )
        data = evolver.load_data()
        parents = [StrategyDNA()]
        results = evolver.run_generation(parents, data)
        assert len(results) == 3

    def test_run_generation_sorted_by_fitness(self, tmp_path):
        data_dir = _make_data_dir(tmp_path, n_stocks=5, days=150)
        evolver = AutoEvolver(
            data_dir=str(data_dir),
            population_size=15,
            elite_count=5,
            results_dir=str(tmp_path / "results"),
            seed=42,
        )
        data = evolver.load_data()
        results = evolver.run_generation([StrategyDNA()], data)
        for i in range(len(results) - 1):
            assert results[i].fitness >= results[i + 1].fitness


# ────────────────── Save / Load tests ──────────────────


class TestSaveLoad:
    def test_save_and_load_best(self, tmp_path):
        results_dir = str(tmp_path / "results")
        evolver = AutoEvolver(data_dir=".", results_dir=results_dir, seed=42)

        dna = StrategyDNA(min_score=8, hold_days=7)
        result = EvolutionResult(
            dna=dna,
            annual_return=25.0,
            max_drawdown=10.0,
            win_rate=55.0,
            sharpe=1.2,
            calmar=2.5,
            total_trades=100,
            profit_factor=1.8,
            fitness=42.0,
        )
        evolver.save_results(10, [result])

        loaded = evolver.load_best()
        assert loaded is not None
        assert loaded.min_score == 8
        assert loaded.hold_days == 7

    def test_load_best_no_file_returns_none(self, tmp_path):
        evolver = AutoEvolver(data_dir=".", results_dir=str(tmp_path / "nope"), seed=42)
        assert evolver.load_best() is None

    def test_save_creates_versioned_file(self, tmp_path):
        results_dir = str(tmp_path / "results")
        evolver = AutoEvolver(data_dir=".", results_dir=results_dir, seed=42)
        dna = StrategyDNA()
        result = EvolutionResult(
            dna=dna, annual_return=10, max_drawdown=5, win_rate=50,
            sharpe=1.0, calmar=2.0, total_trades=50, profit_factor=1.5, fitness=10,
        )
        evolver.save_results(42, [result])

        assert os.path.exists(os.path.join(results_dir, "gen_0042.json"))
        assert os.path.exists(os.path.join(results_dir, "latest.json"))

    def test_resume_from_saved(self, tmp_path):
        """Engine should resume from saved generation number."""
        results_dir = str(tmp_path / "results")
        evolver = AutoEvolver(data_dir=".", results_dir=results_dir, seed=42)

        dna = StrategyDNA()
        result = EvolutionResult(
            dna=dna, annual_return=10, max_drawdown=5, win_rate=50,
            sharpe=1.0, calmar=2.0, total_trades=50, profit_factor=1.5, fitness=10,
        )
        evolver.save_results(15, [result])

        parents = evolver._load_parents()
        start_gen = evolver._load_start_gen()
        assert len(parents) == 1
        assert start_gen == 16  # should resume from gen 16


# ────────────────── End-to-end evolution test ──────────────────


class TestEvolve:
    def test_evolve_small_run(self, tmp_path):
        """Full evolve loop with 3 generations should complete."""
        data_dir = _make_data_dir(tmp_path, n_stocks=5, days=120)
        results_dir = str(tmp_path / "results")
        evolver = AutoEvolver(
            data_dir=str(data_dir),
            population_size=6,
            elite_count=2,
            mutation_rate=0.5,
            results_dir=results_dir,
            seed=42,
        )
        results = evolver.evolve(generations=3, save_interval=2)
        assert len(results) == 2
        assert results[0].fitness >= results[1].fitness

        # Check that results were saved
        assert os.path.exists(os.path.join(results_dir, "latest.json"))
