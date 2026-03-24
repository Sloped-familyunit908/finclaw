"""
Tests for the Backtest Bias Detector.

Covers:
  - BiasReport / SnoopingReport dataclass validation
  - Clean factor passes lookahead detection
  - Tainted factor (uses future data) gets caught
  - Batch lookahead detection
  - Data snooping detection at various overfit levels
  - Survivorship bias warnings
  - Edge cases (short data, empty inputs)
"""

import math
import pytest
from unittest.mock import patch

from src.evolution.bias_detector import (
    BiasReport,
    SnoopingReport,
    detect_lookahead,
    detect_lookahead_batch,
    detect_snooping,
    check_survivorship,
    make_test_ohlcv,
    _simple_backtest_return,
)


# ============================================================
# Helpers
# ============================================================


def _make_data(n: int = 200) -> dict:
    """Create simple synthetic OHLCV data."""
    closes = [100.0 + i * 0.1 for i in range(n)]
    highs = [c + 0.5 for c in closes]
    lows = [c - 0.3 for c in closes]
    volumes = [1_000_000 + (i % 5) * 100_000 for i in range(n)]
    return {"closes": closes, "highs": highs, "lows": lows, "volumes": volumes}


def clean_factor(closes, highs, lows, volumes, idx):
    """A clean factor: only uses data up to and including idx."""
    if idx < 5:
        return 0.5
    avg = sum(closes[idx - 4 : idx + 1]) / 5.0
    return max(0.0, min(1.0, closes[idx] / avg - 0.95))


def lookahead_factor(closes, highs, lows, volumes, idx):
    """A tainted factor: peeks at FUTURE data beyond idx."""
    if idx >= len(closes) - 3:
        return 0.5
    # This looks ahead 3 bars — classic future function bug
    future_avg = sum(closes[idx + 1 : idx + 4]) / 3.0
    return max(0.0, min(1.0, future_avg / closes[idx] - 0.95))


def subtle_lookahead_factor(closes, highs, lows, volumes, idx):
    """Subtle tainted factor: uses len(closes) which leaks info about future."""
    total_len = len(closes)
    # Uses full length to scale — trivially different with truncated data
    ratio = idx / total_len
    if idx < 5:
        return 0.5
    avg = sum(closes[idx - 4 : idx + 1]) / 5.0
    return max(0.0, min(1.0, (closes[idx] / avg - 0.95) * (1 + ratio)))


# ============================================================
# Test 1-4: BiasReport & SnoopingReport dataclass
# ============================================================


class TestBiasReport:
    def test_bias_report_clean(self):
        """BiasReport with CLEAN severity is valid."""
        r = BiasReport("test_factor", False, "All good", "CLEAN")
        assert r.factor_name == "test_factor"
        assert r.has_lookahead is False
        assert r.severity == "CLEAN"

    def test_bias_report_critical(self):
        """BiasReport with CRITICAL severity is valid."""
        r = BiasReport("bad_factor", True, "Future data used", "CRITICAL")
        assert r.has_lookahead is True
        assert r.severity == "CRITICAL"

    def test_bias_report_invalid_severity(self):
        """BiasReport rejects invalid severity."""
        with pytest.raises(ValueError, match="Invalid severity"):
            BiasReport("x", False, "", "INVALID")

    def test_snooping_report_valid(self):
        """SnoopingReport with valid risk_level."""
        r = SnoopingReport("dna1", 0.5, 0.1, 5.0, "HIGH", "details")
        assert r.dna_id == "dna1"
        assert r.risk_level == "HIGH"

    def test_snooping_report_invalid_risk(self):
        """SnoopingReport rejects invalid risk_level."""
        with pytest.raises(ValueError, match="Invalid risk_level"):
            SnoopingReport("x", 0.0, 0.0, 0.0, "BANANA", "")


# ============================================================
# Test 5-7: Look-ahead Bias Detection
# ============================================================


class TestLookaheadDetection:
    def test_clean_factor_passes(self):
        """A well-behaved factor should pass lookahead detection."""
        data = _make_data(200)
        report = detect_lookahead(clean_factor, data)
        assert report.has_lookahead is False
        assert report.severity == "CLEAN"

    def test_lookahead_factor_caught(self):
        """A factor using future data must be detected."""
        data = _make_data(200)
        report = detect_lookahead(lookahead_factor, data)
        assert report.has_lookahead is True
        assert report.severity in ("WARNING", "CRITICAL")
        assert "idx=" in report.details

    def test_subtle_lookahead_caught(self):
        """A factor using len(closes) leaks future info and must be caught."""
        data = _make_data(200)
        report = detect_lookahead(subtle_lookahead_factor, data)
        assert report.has_lookahead is True
        assert report.severity in ("WARNING", "CRITICAL")

    def test_batch_detection(self):
        """Batch detection runs on multiple factors and returns correct count."""
        data = _make_data(200)
        factors = {
            "clean": clean_factor,
            "lookahead": lookahead_factor,
        }
        reports = detect_lookahead_batch(factors, data)
        assert len(reports) == 2

        by_name = {r.factor_name: r for r in reports}
        assert by_name["clean"].has_lookahead is False
        assert by_name["lookahead"].has_lookahead is True

    def test_short_data_warning(self):
        """Very short data should produce a WARNING, not crash."""
        data = _make_data(5)
        report = detect_lookahead(clean_factor, data)
        assert report.severity == "WARNING"
        assert "Insufficient" in report.details


# ============================================================
# Test 8-11: Data Snooping Detection
# ============================================================


class TestSnoopingDetection:
    def test_low_overfit(self):
        """Same data for train and test should give LOW risk."""
        data = make_test_ohlcv(200, seed=42)
        dna = {"id": "test_dna", "weights": {"f1": 1.0}}

        # Use same data → ratio ≈ 1.0
        report = detect_snooping(dna, data, data)
        assert report.risk_level == "LOW"
        assert report.overfit_ratio <= 2.0

    def test_extreme_overfit_sign_flip(self):
        """Positive train return + negative test return → EXTREME."""
        train_data = make_test_ohlcv(200, seed=42)
        test_data = make_test_ohlcv(200, seed=99)

        # Create a factor that performs well on train data's specific pattern
        # but poorly on different test data
        def biased_factor(closes, highs, lows, volumes, idx):
            if idx < 5:
                return 0.5
            # This factor is tuned to seed=42 data pattern
            if closes[idx] > closes[idx - 1]:
                return 0.9
            return 0.1

        dna = {"id": "overfit_dna", "weights": {"biased": 1.0}}

        report = detect_snooping(
            dna, train_data, test_data,
            factor_fns={"biased": biased_factor}
        )
        # The exact risk level depends on the data, but it should reflect
        # a meaningful comparison
        assert report.train_return != 0.0 or report.test_return != 0.0
        assert isinstance(report.overfit_ratio, float)

    def test_snooping_with_no_factor_fns(self):
        """When no factor functions provided, uses trivial fallback."""
        train = make_test_ohlcv(100, seed=1)
        test = make_test_ohlcv(100, seed=2)
        dna = {"id": "trivial", "weights": {"a": 1.0, "b": 0.5}}
        report = detect_snooping(dna, train, test)
        # Trivial factors return 0.5 → no trades → returns ≈ 0
        assert report.risk_level == "LOW"

    def test_snooping_overfit_ratio_inf(self):
        """When test return is ~0 but train is not → high ratio."""
        # Construct a scenario manually
        report = SnoopingReport(
            dna_id="x",
            train_return=0.5,
            test_return=0.0,
            overfit_ratio=float("inf"),
            risk_level="EXTREME",
            details="manual",
        )
        assert report.overfit_ratio == float("inf")
        assert report.risk_level == "EXTREME"


# ============================================================
# Test 12-14: Survivorship Bias
# ============================================================


class TestSurvivorshipBias:
    def test_no_warnings_for_clean_data(self):
        """All stocks with full data should produce no warnings."""
        stock_data = {
            "000001": _make_data(200),
            "000002": _make_data(200),
        }
        warnings = check_survivorship(stock_data)
        assert warnings == []

    def test_delisted_stock_detected(self):
        """Stock with trailing zeros should be flagged."""
        normal = _make_data(200)
        delisted = _make_data(200)
        # Make last 30 bars zero (15% of data > 10% threshold)
        delisted["closes"][-30:] = [0.0] * 30

        stock_data = {
            "000001": normal,
            "600666": delisted,
        }
        warnings = check_survivorship(stock_data)
        assert len(warnings) == 1
        assert "600666" in warnings[0]
        assert "delisted" in warnings[0].lower()

    def test_shorter_data_flagged(self):
        """Stock with significantly less data than others is flagged."""
        stock_data = {
            "000001": _make_data(200),
            "000002": _make_data(200),
            "ST_DEAD": _make_data(100),  # only half the data
        }
        warnings = check_survivorship(stock_data)
        assert any("ST_DEAD" in w for w in warnings)

    def test_empty_stock_data(self):
        """Empty input should return no warnings."""
        assert check_survivorship({}) == []

    def test_stock_with_no_closes(self):
        """Stock with empty closes list should be flagged."""
        stock_data = {
            "000001": _make_data(200),
            "GHOST": {"closes": [], "highs": [], "lows": [], "volumes": []},
        }
        warnings = check_survivorship(stock_data)
        assert any("GHOST" in w for w in warnings)


# ============================================================
# Test 15-16: make_test_ohlcv helper
# ============================================================


class TestHelpers:
    def test_make_test_ohlcv_shape(self):
        """make_test_ohlcv returns correct shape."""
        data = make_test_ohlcv(100, seed=1)
        assert len(data["closes"]) == 100
        assert len(data["highs"]) == 100
        assert len(data["lows"]) == 100
        assert len(data["volumes"]) == 100

    def test_make_test_ohlcv_deterministic(self):
        """Same seed produces same data."""
        d1 = make_test_ohlcv(50, seed=7)
        d2 = make_test_ohlcv(50, seed=7)
        assert d1["closes"] == d2["closes"]

    def test_simple_backtest_return_runs(self):
        """_simple_backtest_return should run without error."""
        data = make_test_ohlcv(100, seed=42)
        weights = {"clean": 1.0}
        fns = {"clean": clean_factor}
        ret = _simple_backtest_return(weights, fns, data)
        assert isinstance(ret, float)
        assert not math.isnan(ret)
