"""Tests for fundamental factors integration.

Covers: scoring functions, StrategyDNA fields, score_stock integration,
        and weight normalization with 15 dimensions.
"""

import math
import random

import pytest

from src.evolution.fundamentals import (
    compute_growth_score,
    compute_pb_score,
    compute_pe_score,
    compute_roe_score,
)
from src.evolution.auto_evolve import (
    StrategyDNA,
    _WEIGHT_KEYS,
    _PARAM_RANGES,
    AutoEvolver,
    score_stock,
)


# ────────────────── PE Score ──────────────────


class TestPEScore:
    def test_negative_pe_returns_zero(self):
        assert compute_pe_score(-5.0) == 0.0

    def test_zero_pe_returns_zero(self):
        assert compute_pe_score(0.0) == 0.0

    def test_very_high_pe_returns_zero(self):
        assert compute_pe_score(250.0) == 0.0

    def test_very_low_pe_high_score(self):
        # PE = 10, sector avg = 25 → ratio = 0.4 < 0.5 → score = 1.0
        assert compute_pe_score(10.0) == 1.0

    def test_pe_at_sector_avg(self):
        # PE = 25, ratio = 1.0 → should be around 0.5
        score = compute_pe_score(25.0)
        assert 0.45 <= score <= 0.55

    def test_pe_double_sector_avg(self):
        # PE = 50, ratio = 2.0 → should be low
        score = compute_pe_score(50.0)
        assert score < 0.2

    def test_pe_half_sector_avg(self):
        # PE = 12.5, ratio = 0.5 → at boundary (ratio < 0.5 is false, enters next branch)
        score = compute_pe_score(12.5)
        assert score == 0.8  # ratio = 0.5 enters the elif ratio < 1.0 branch

    def test_pe_returns_between_0_and_1(self):
        for pe in [1, 5, 10, 15, 20, 25, 30, 50, 100, 199]:
            score = compute_pe_score(float(pe))
            assert 0.0 <= score <= 1.0, f"PE={pe} gave score={score}"

    def test_custom_sector_avg(self):
        # PE = 10, sector avg = 10 → ratio = 1.0
        score = compute_pe_score(10.0, sector_avg_pe=10.0)
        assert 0.45 <= score <= 0.55


# ────────────────── Growth Score ──────────────────


class TestGrowthScore:
    def test_very_high_growth(self):
        assert compute_growth_score(60.0) == 1.0

    def test_high_growth(self):
        assert compute_growth_score(35.0) == 0.8

    def test_moderate_growth(self):
        assert compute_growth_score(20.0) == 0.6

    def test_low_growth(self):
        assert compute_growth_score(5.0) == 0.4

    def test_slight_decline(self):
        assert compute_growth_score(-5.0) == 0.2

    def test_severe_decline(self):
        assert compute_growth_score(-15.0) == 0.0

    def test_zero_growth(self):
        # 0% is > -10, so should be 0.4 (> 0 branch)
        assert compute_growth_score(0.1) == 0.4

    def test_boundary_50(self):
        assert compute_growth_score(50.0) == 0.8  # > 30, not > 50

    def test_boundary_exactly_50_point_1(self):
        assert compute_growth_score(50.1) == 1.0


# ────────────────── ROE Score ──────────────────


class TestROEScore:
    def test_very_high_roe(self):
        assert compute_roe_score(30.0) == 1.0

    def test_high_roe(self):
        assert compute_roe_score(20.0) == 0.8

    def test_moderate_roe(self):
        assert compute_roe_score(12.0) == 0.6

    def test_low_roe(self):
        assert compute_roe_score(7.0) == 0.4

    def test_very_low_roe(self):
        assert compute_roe_score(2.0) == 0.2

    def test_negative_roe(self):
        assert compute_roe_score(-5.0) == 0.0

    def test_zero_roe(self):
        assert compute_roe_score(0.0) == 0.0

    def test_boundary_25(self):
        assert compute_roe_score(25.0) == 0.8  # > 15, not > 25


# ────────────────── PB Score ──────────────────


class TestPBScore:
    def test_negative_pb_returns_zero(self):
        assert compute_pb_score(-1.0) == 0.0

    def test_zero_pb_returns_zero(self):
        assert compute_pb_score(0.0) == 0.0

    def test_below_book_value(self):
        assert compute_pb_score(0.8) == 1.0

    def test_low_pb(self):
        assert compute_pb_score(1.5) == 0.7

    def test_moderate_pb(self):
        assert compute_pb_score(2.5) == 0.5

    def test_high_pb(self):
        assert compute_pb_score(4.0) == 0.3

    def test_very_high_pb(self):
        assert compute_pb_score(10.0) == 0.1

    def test_pb_boundary_1(self):
        # pb = 1.0 is >= 1.0, not < 1.0 → enters the elif pb < 2.0 branch
        assert compute_pb_score(1.0) == 0.7

    def test_pb_returns_between_0_and_1(self):
        for pb in [0.1, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0, 50.0]:
            score = compute_pb_score(pb)
            assert 0.0 <= score <= 1.0, f"PB={pb} gave score={score}"


# ────────────────── StrategyDNA Fundamental Fields ──────────────────


class TestStrategyDNAFundamentals:
    def test_has_pe_field(self):
        dna = StrategyDNA()
        assert hasattr(dna, "w_pe")
        assert dna.w_pe == 0.0

    def test_has_pb_field(self):
        dna = StrategyDNA()
        assert hasattr(dna, "w_pb")
        assert dna.w_pb == 0.0

    def test_has_roe_field(self):
        dna = StrategyDNA()
        assert hasattr(dna, "w_roe")
        assert dna.w_roe == 0.0

    def test_has_revenue_growth_field(self):
        dna = StrategyDNA()
        assert hasattr(dna, "w_revenue_growth")
        assert dna.w_revenue_growth == 0.0

    def test_fundamental_weights_default_zero(self):
        """All fundamental weights should default to 0 — evolution discovers optimal."""
        dna = StrategyDNA()
        assert dna.w_pe == 0.0
        assert dna.w_pb == 0.0
        assert dna.w_roe == 0.0
        assert dna.w_revenue_growth == 0.0

    def test_fundamental_weights_in_weight_keys(self):
        assert "w_pe" in _WEIGHT_KEYS
        assert "w_pb" in _WEIGHT_KEYS
        assert "w_roe" in _WEIGHT_KEYS
        assert "w_revenue_growth" in _WEIGHT_KEYS

    def test_fundamental_weights_in_param_ranges(self):
        for key in ["w_pe", "w_pb", "w_roe", "w_revenue_growth"]:
            assert key in _PARAM_RANGES
            lo, hi, is_int = _PARAM_RANGES[key]
            assert lo == 0.0
            assert hi == 1.0
            assert is_int is False

    def test_weight_keys_count_is_15(self):
        """11 technical + 4 fundamental = 15 weight keys."""
        assert len(_WEIGHT_KEYS) == 15

    def test_to_dict_includes_fundamentals(self):
        dna = StrategyDNA(w_pe=0.1, w_roe=0.2)
        d = dna.to_dict()
        assert d["w_pe"] == 0.1
        assert d["w_roe"] == 0.2

    def test_from_dict_restores_fundamentals(self):
        d = StrategyDNA(w_pe=0.15, w_pb=0.05).to_dict()
        restored = StrategyDNA.from_dict(d)
        assert restored.w_pe == 0.15
        assert restored.w_pb == 0.05


# ────────────────── Score Stock with Fundamentals ──────────────────


class TestScoreStockFundamentals:
    def _make_indicators(self, n=100):
        """Create minimal valid indicators for scoring."""
        return {
            "rsi": [float("nan")] * 20 + [40.0] * (n - 20),
            "r2": [float("nan")] * 20 + [0.7] * (n - 20),
            "slope": [float("nan")] * 20 + [1.0] * (n - 20),
            "volume_ratio": [float("nan")] * 20 + [1.5] * (n - 20),
            "close": [100.0 + i * 0.5 for i in range(n)],
            "open": [100.0 + i * 0.5 for i in range(n)],
            "high": [101.0 + i * 0.5 for i in range(n)],
            "low": [99.0 + i * 0.5 for i in range(n)],
            "volume": [1_000_000.0] * n,
        }

    def test_score_with_no_fundamentals(self):
        """Score should work even when fundamentals are missing."""
        indicators = self._make_indicators()
        dna = StrategyDNA()
        score = score_stock(50, indicators, dna)
        assert 0 <= score <= 10

    def test_score_with_empty_fundamentals(self):
        """Score should handle empty fundamentals dict gracefully."""
        indicators = self._make_indicators()
        indicators["fundamentals"] = {}
        dna = StrategyDNA()
        score = score_stock(50, indicators, dna)
        assert 0 <= score <= 10

    def test_score_with_full_fundamentals(self):
        """Score should incorporate valid fundamental data."""
        indicators = self._make_indicators()
        indicators["fundamentals"] = {
            "pe": 15.0,
            "pb": 1.5,
            "roe": 18.0,
            "revenue_growth": 25.0,
        }
        # Enable fundamental weights
        dna = StrategyDNA(
            w_pe=0.1, w_pb=0.1, w_roe=0.1, w_revenue_growth=0.1,
            # Reduce other weights proportionally
            w_momentum=0.05, w_mean_reversion=0.05, w_volume=0.05,
            w_trend=0.05, w_pattern=0.05, w_macd=0.05,
            w_bollinger=0.05, w_kdj=0.05, w_obv=0.05,
            w_support=0.05, w_volume_profile=0.05,
        )
        score = score_stock(50, indicators, dna)
        assert 0 <= score <= 10

    def test_score_with_zero_fundamental_weights(self):
        """With all fundamental weights at 0, fundamentals should not affect score."""
        indicators1 = self._make_indicators()
        indicators2 = self._make_indicators()
        indicators2["fundamentals"] = {
            "pe": 100.0, "pb": 10.0, "roe": 0.5, "revenue_growth": -50.0
        }

        dna = StrategyDNA()  # defaults have w_pe=w_pb=w_roe=w_revenue_growth=0
        score1 = score_stock(50, indicators1, dna)
        score2 = score_stock(50, indicators2, dna)
        assert score1 == pytest.approx(score2, abs=0.01)


# ────────────────── Weight Normalization with 15 Dimensions ──────────────────


class TestWeightNormalization:
    def test_mutation_normalizes_15_weights(self):
        """After mutation, all 15 weights should sum ≈ 1.0."""
        evolver = AutoEvolver(data_dir=".", mutation_rate=1.0, seed=42)
        dna = StrategyDNA()
        for _ in range(50):
            mutated = evolver.mutate(dna)
            w_sum = sum(getattr(mutated, k) for k in _WEIGHT_KEYS)
            assert abs(w_sum - 1.0) < 0.02, f"Weights sum to {w_sum}, expected ≈1.0"

    def test_crossover_normalizes_15_weights(self):
        """After crossover, all 15 weights should sum ≈ 1.0."""
        evolver = AutoEvolver(data_dir=".", seed=42)
        dna1 = StrategyDNA(w_pe=0.2, w_roe=0.3)
        dna2 = StrategyDNA(w_pb=0.4, w_revenue_growth=0.1)
        for _ in range(50):
            child = evolver.crossover(dna1, dna2)
            w_sum = sum(getattr(child, k) for k in _WEIGHT_KEYS)
            assert abs(w_sum - 1.0) < 0.02, f"Weights sum to {w_sum}, expected ≈1.0"

    def test_all_weight_keys_have_param_ranges(self):
        """Every key in _WEIGHT_KEYS should have an entry in _PARAM_RANGES."""
        for k in _WEIGHT_KEYS:
            assert k in _PARAM_RANGES, f"{k} missing from _PARAM_RANGES"

    def test_all_weight_keys_are_dna_fields(self):
        """Every key in _WEIGHT_KEYS should be a StrategyDNA field."""
        dna = StrategyDNA()
        for k in _WEIGHT_KEYS:
            assert hasattr(dna, k), f"{k} not found in StrategyDNA"
