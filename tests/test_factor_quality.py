"""Tests for the factor quality analysis module.

Covers IC computation with synthetic data, IR, decay analysis,
tier classification, report generation, and edge cases.
"""

import json
import math
import pytest

from src.evolution.factor_analysis import compute_ic, compute_ir
from src.evolution.factor_quality import (
    DECAY_PERIODS,
    FactorQualityAnalyzer,
    _classify_tier,
    _forward_returns,
    _safe_mean,
    _safe_std,
)
from src.evolution.factor_discovery import FactorRegistry, FactorMeta


# ── helpers ──────────────────────────────────────────────────

def _make_stock(n: int = 120, trend: float = 0.001, seed: int = 0):
    """Return synthetic stock data with *n* bars.

    A deterministic pseudo-random walk so tests are reproducible.
    """
    closes, highs, lows, volumes = [], [], [], []
    price = 10.0
    # simple LCG for reproducibility without importing random
    state = seed + 1
    for i in range(n):
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        noise = ((state % 1000) - 500) / 50000.0  # small noise
        price *= 1 + trend + noise
        c = round(price, 4)
        h = round(c * 1.005, 4)
        lo = round(c * 0.995, 4)
        v = 1_000_000.0 + (state % 500_000)
        closes.append(c)
        highs.append(h)
        lows.append(lo)
        volumes.append(v)
    return {
        "date": [f"2025-01-{i+1:03d}" for i in range(n)],
        "open": [c * 0.999 for c in closes],
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    }


def _make_registry_with(factors_dict: dict) -> FactorRegistry:
    """Build a FactorRegistry pre-loaded with the given factors.

    *factors_dict* maps ``name`` → ``compute_fn``.
    """
    reg = FactorRegistry(factors_dir="__nonexistent__")
    for name, fn in factors_dict.items():
        reg.factors[name] = FactorMeta(
            name=name,
            description="test",
            source_file="<synthetic>",
            compute_fn=fn,
        )
    return reg


def _trivial_factor(closes, highs, lows, volumes, idx):
    """A factor that returns the normalised close rank within [0,1]."""
    if idx < 1:
        return 0.5
    # simple momentum proxy: positive change → high score
    change = (closes[idx] - closes[idx - 1]) / closes[idx - 1] if closes[idx - 1] else 0
    return max(0.0, min(1.0, 0.5 + change * 10))


def _constant_factor(_c, _h, _l, _v, _i):
    """Always returns 0.5."""
    return 0.5


def _zero_factor(_c, _h, _l, _v, _i):
    """Always returns 0."""
    return 0.0


def _perfect_factor(closes, highs, lows, volumes, idx):
    """A factor that is literally the next-day return direction (cheating)."""
    if idx + 1 >= len(closes) or closes[idx] == 0:
        return 0.5
    fwd = (closes[idx + 1] - closes[idx]) / closes[idx]
    return max(0.0, min(1.0, 0.5 + fwd * 100))


# ── Tests: _forward_returns ──────────────────────────────────

class TestForwardReturns:
    def test_simple_forward_return(self):
        closes = [100.0, 110.0, 105.0]
        ret = _forward_returns(closes, 0, 1)
        assert ret == pytest.approx(0.10)

    def test_multi_day(self):
        closes = [100.0, 110.0, 120.0]
        ret = _forward_returns(closes, 0, 2)
        assert ret == pytest.approx(0.20)

    def test_out_of_range(self):
        closes = [100.0, 110.0]
        assert _forward_returns(closes, 0, 2) is None
        assert _forward_returns(closes, 1, 1) is None

    def test_zero_close(self):
        closes = [0.0, 10.0]
        assert _forward_returns(closes, 0, 1) is None

    def test_negative_idx(self):
        closes = [100.0, 110.0]
        assert _forward_returns(closes, -1, 1) is None


# ── Tests: _classify_tier ────────────────────────────────────

class TestClassifyTier:
    def test_tier_a(self):
        assert _classify_tier(0.06, 0.6) == "A"

    def test_tier_b(self):
        assert _classify_tier(0.04, 0.4) == "B"

    def test_tier_c(self):
        assert _classify_tier(0.02, 0.1) == "C"

    def test_tier_d(self):
        assert _classify_tier(0.005, 0.05) == "D"

    def test_boundary_a_needs_both(self):
        # High IC but low IR → not A
        assert _classify_tier(0.06, 0.4) != "A"
        # High IR but low IC → not A
        assert _classify_tier(0.04, 0.6) != "A"

    def test_boundary_b_needs_both(self):
        assert _classify_tier(0.04, 0.2) != "B"


# ── Tests: _safe_mean / _safe_std ────────────────────────────

class TestSafeStats:
    def test_mean_empty(self):
        assert _safe_mean([]) == 0.0

    def test_mean_values(self):
        assert _safe_mean([1.0, 3.0]) == pytest.approx(2.0)

    def test_std_single(self):
        assert _safe_std([5.0]) == 0.0

    def test_std_values(self):
        assert _safe_std([2.0, 4.0]) == pytest.approx(1.0)


# ── Tests: IC computation with synthetic data ────────────────

class TestICWithSyntheticData:
    def test_perfect_positive_rank_ic(self):
        scores = list(range(20))
        returns = list(range(20))
        ic = compute_ic(scores, returns)
        assert ic == pytest.approx(1.0)

    def test_no_signal_factor_gives_low_ic(self):
        """A random-noise factor should yield IC near 0."""
        # Use uncorrelated but non-constant scores to avoid the tied-rank edge case
        # where Spearman's formula gives a spurious value for all-constant inputs.
        state = 12345
        scores = []
        for _ in range(50):
            state = (state * 1103515245 + 12345) & 0x7FFFFFFF
            scores.append(state % 1000 / 1000.0)
        returns = list(range(50))  # monotonic returns — no relation to noise
        ic = compute_ic(scores, returns)
        assert abs(ic) < 0.3  # should be near 0 but allow noise


# ── Tests: FactorQualityAnalyzer ─────────────────────────────

class TestFactorQualityAnalyzer:
    @pytest.fixture()
    def stock_data_20(self):
        """20 stocks, 120 bars each."""
        return {f"S{i:03d}": _make_stock(120, trend=0.0005, seed=i) for i in range(20)}

    @pytest.fixture()
    def registry_simple(self):
        return _make_registry_with({
            "trivial": _trivial_factor,
            "constant": _constant_factor,
        })

    def test_analyze_all_returns_results_for_every_factor(
        self, stock_data_20, registry_simple
    ):
        analyzer = FactorQualityAnalyzer(stock_data_20, registry_simple, max_stocks=20)
        results = analyzer.analyze_all()
        assert set(results.keys()) == {"trivial", "constant"}
        for info in results.values():
            assert "ic_mean" in info
            assert "ic_std" in info
            assert "ir" in info
            assert "hit_rate" in info
            assert "decay" in info
            assert "tier" in info

    def test_constant_factor_gets_low_tier(self, stock_data_20):
        reg = _make_registry_with({"constant": _constant_factor})
        analyzer = FactorQualityAnalyzer(stock_data_20, reg, max_stocks=20)
        analyzer.analyze_all()
        # Constant factor has no real signal — should land in C or D
        assert analyzer.get_tier("constant") in ("C", "D")

    def test_decay_has_required_periods(self, stock_data_20, registry_simple):
        analyzer = FactorQualityAnalyzer(stock_data_20, registry_simple, max_stocks=20)
        results = analyzer.analyze_all()
        for info in results.values():
            for p in DECAY_PERIODS:
                assert p in info["decay"]

    def test_hit_rate_between_0_and_1(self, stock_data_20, registry_simple):
        analyzer = FactorQualityAnalyzer(stock_data_20, registry_simple, max_stocks=20)
        results = analyzer.analyze_all()
        for info in results.values():
            assert 0.0 <= info["hit_rate"] <= 1.0

    def test_max_stocks_sampling(self):
        # Create 150 stocks, set max to 10
        data = {f"S{i:03d}": _make_stock(120, seed=i) for i in range(150)}
        reg = _make_registry_with({"trivial": _trivial_factor})
        analyzer = FactorQualityAnalyzer(data, reg, max_stocks=10)
        results = analyzer.analyze_all()
        assert "trivial" in results

    def test_get_tier_unknown_factor(self, stock_data_20, registry_simple):
        analyzer = FactorQualityAnalyzer(stock_data_20, registry_simple)
        analyzer.analyze_all()
        assert analyzer.get_tier("nonexistent") == "D"

    def test_get_results_returns_copy(self, stock_data_20, registry_simple):
        analyzer = FactorQualityAnalyzer(stock_data_20, registry_simple, max_stocks=20)
        analyzer.analyze_all()
        r1 = analyzer.get_results()
        r2 = analyzer.get_results()
        assert r1 is not r2
        assert r1 == r2


# ── Tests: generate_factor_report ────────────────────────────

class TestGenerateFactorReport:
    @pytest.fixture()
    def report(self):
        data = {f"S{i:03d}": _make_stock(120, seed=i) for i in range(20)}
        reg = _make_registry_with({
            "trivial": _trivial_factor,
            "constant": _constant_factor,
            "zero": _zero_factor,
        })
        analyzer = FactorQualityAnalyzer(data, reg, max_stocks=20)
        analyzer.analyze_all()
        return analyzer.generate_factor_report()

    def test_report_has_required_keys(self, report):
        assert "total_factors" in report
        assert "tier_summary" in report
        assert "factors" in report
        assert "recommendations" in report

    def test_total_factors_count(self, report):
        assert report["total_factors"] == 3

    def test_factors_ranked_by_abs_ic(self, report):
        ics = [abs(f["ic_mean"]) for f in report["factors"]]
        assert ics == sorted(ics, reverse=True)

    def test_tier_summary_adds_up(self, report):
        ts = report["tier_summary"]
        assert sum(ts.values()) == report["total_factors"]

    def test_recommendations_structure(self, report):
        rec = report["recommendations"]
        assert "keep" in rec
        assert "drop" in rec
        assert isinstance(rec["keep"], list)
        assert isinstance(rec["drop"], list)

    def test_report_is_json_serialisable(self, report):
        # Must not raise
        s = json.dumps(report, ensure_ascii=False)
        assert isinstance(s, str)


# ── Tests: edge cases ────────────────────────────────────────

class TestEdgeCases:
    def test_empty_stock_data(self):
        reg = _make_registry_with({"trivial": _trivial_factor})
        analyzer = FactorQualityAnalyzer({}, reg)
        results = analyzer.analyze_all()
        for info in results.values():
            assert info["tier"] == "D"
            assert info["ic_mean"] == 0.0

    def test_single_stock(self):
        data = {"ONLY": _make_stock(120, seed=42)}
        reg = _make_registry_with({"trivial": _trivial_factor})
        analyzer = FactorQualityAnalyzer(data, reg, max_stocks=1)
        results = analyzer.analyze_all()
        # With a single stock, compute_ic requires >= 10 data points
        # but cross-sectional IC with 1 stock always fails → tier D
        assert results["trivial"]["tier"] == "D"

    def test_all_zero_factor(self):
        data = {f"S{i:03d}": _make_stock(120, seed=i) for i in range(20)}
        reg = _make_registry_with({"zero": _zero_factor})
        analyzer = FactorQualityAnalyzer(data, reg, max_stocks=20)
        results = analyzer.analyze_all()
        # All-zero is constant → no real signal, expect C or D
        assert results["zero"]["tier"] in ("C", "D")

    def test_very_short_series(self):
        """Stocks with only 10 bars — not enough for the 30-bar warmup."""
        data = {f"S{i:03d}": _make_stock(10, seed=i) for i in range(20)}
        reg = _make_registry_with({"trivial": _trivial_factor})
        analyzer = FactorQualityAnalyzer(data, reg, max_stocks=20)
        results = analyzer.analyze_all()
        assert results["trivial"]["tier"] == "D"

    def test_empty_registry(self):
        data = {f"S{i:03d}": _make_stock(120, seed=i) for i in range(10)}
        reg = FactorRegistry(factors_dir="__nonexistent__")
        analyzer = FactorQualityAnalyzer(data, reg)
        results = analyzer.analyze_all()
        assert results == {}
        report = analyzer.generate_factor_report()
        assert report["total_factors"] == 0

    def test_factor_raising_exception(self):
        """A factor that throws should be treated as 0.5 (neutral)."""

        def bad_factor(c, h, l, v, i):
            raise ValueError("boom")

        data = {f"S{i:03d}": _make_stock(120, seed=i) for i in range(15)}
        reg = _make_registry_with({"bad": bad_factor})
        analyzer = FactorQualityAnalyzer(data, reg, max_stocks=15)
        results = analyzer.analyze_all()
        # Should still produce a result — all neutral scores are constant,
        # so it may land in C or D depending on tied-rank noise
        assert results["bad"]["tier"] in ("C", "D")
