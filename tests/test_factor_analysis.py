"""Tests for factor analysis module."""
import pytest
from src.evolution.factor_analysis import (
    compute_ic,
    compute_ir,
    compute_factor_returns,
    analyze_factor_decay,
    _rank,
)


class TestRank:
    def test_basic_ranking(self):
        assert _rank([3.0, 1.0, 2.0]) == [3.0, 1.0, 2.0]

    def test_ties(self):
        ranks = _rank([1.0, 2.0, 2.0, 4.0])
        assert ranks[0] == 1.0
        assert ranks[1] == 2.5  # tied
        assert ranks[2] == 2.5  # tied
        assert ranks[3] == 4.0

    def test_single_element(self):
        assert _rank([5.0]) == [1.0]

    def test_all_same(self):
        ranks = _rank([1.0, 1.0, 1.0])
        assert ranks == [2.0, 2.0, 2.0]


class TestComputeIC:
    def test_perfect_positive_correlation(self):
        scores = list(range(20))
        returns = list(range(20))
        ic = compute_ic(scores, returns)
        assert ic == 1.0

    def test_perfect_negative_correlation(self):
        scores = list(range(20))
        returns = list(range(19, -1, -1))
        ic = compute_ic(scores, returns)
        assert ic == -1.0

    def test_no_correlation(self):
        # Alternating pattern should give low IC
        scores = list(range(20))
        returns = [1, -1] * 10
        ic = compute_ic(scores, returns)
        assert abs(ic) < 0.3

    def test_too_few_data_points(self):
        assert compute_ic([1, 2, 3], [1, 2, 3]) == 0.0

    def test_exactly_10_points(self):
        scores = list(range(10))
        returns = list(range(10))
        ic = compute_ic(scores, returns)
        assert ic == 1.0

    def test_empty(self):
        assert compute_ic([], []) == 0.0


class TestComputeIR:
    def test_consistent_positive_ics(self):
        # Consistent ICs → high IR
        ic_series = [0.1, 0.12, 0.09, 0.11, 0.1]
        ir = compute_ir(ic_series)
        assert ir > 1.0  # Very consistent

    def test_inconsistent_ics(self):
        # Noisy ICs → low IR
        ic_series = [0.2, -0.1, 0.15, -0.05, 0.1]
        ir = compute_ir(ic_series)
        assert ir < 1.0

    def test_too_few_data_points(self):
        assert compute_ir([0.1, 0.2, 0.3]) == 0.0

    def test_zero_std(self):
        assert compute_ir([0.1, 0.1, 0.1, 0.1, 0.1]) == 0.0

    def test_negative_mean(self):
        ic_series = [-0.1, -0.12, -0.09, -0.11, -0.1]
        ir = compute_ir(ic_series)
        assert ir < -1.0  # Consistently negative


class TestComputeFactorReturns:
    def test_basic_quintile(self):
        # 10 stocks, factor perfectly predicts returns
        scores = {f"s{i}": float(i) for i in range(10)}
        returns = {f"s{i}": float(i) * 0.01 for i in range(10)}
        result = compute_factor_returns(scores, returns)
        assert result["top_quintile"] > result["bottom_quintile"]
        assert result["long_short"] > 0

    def test_too_few_stocks(self):
        scores = {"a": 1.0, "b": 2.0}
        returns = {"a": 0.01, "b": 0.02}
        result = compute_factor_returns(scores, returns)
        assert result == {"long_short": 0.0, "top_quintile": 0.0, "bottom_quintile": 0.0}

    def test_inverse_factor(self):
        # Factor inversely predicts returns
        scores = {f"s{i}": float(i) for i in range(10)}
        returns = {f"s{i}": float(9 - i) * 0.01 for i in range(10)}
        result = compute_factor_returns(scores, returns)
        assert result["long_short"] < 0

    def test_missing_returns(self):
        scores = {f"s{i}": float(i) for i in range(10)}
        returns = {f"s{i}": float(i) * 0.01 for i in range(5)}  # only half
        result = compute_factor_returns(scores, returns)
        # Should still work, missing returns default to 0
        assert "long_short" in result


class TestAnalyzeFactorDecay:
    def test_basic_decay(self):
        scores = {f"s{i}": float(i) for i in range(20)}
        # Returns that are perfectly correlated for 1d, less so for longer periods
        multi_returns = {
            f"s{i}": [float(i) * 0.01, float(i) * 0.008, float(i) * 0.005, float(i) * 0.002, float(i) * 0.001]
            for i in range(20)
        }
        decay = analyze_factor_decay(scores, multi_returns)
        assert 1 in decay
        assert 20 in decay
        # IC should generally decay over time
        assert decay[1] >= decay[20]

    def test_missing_data(self):
        scores = {f"s{i}": float(i) for i in range(20)}
        # Missing some stocks in returns
        multi_returns = {
            f"s{i}": [float(i) * 0.01] * 5
            for i in range(10)  # only half
        }
        decay = analyze_factor_decay(scores, multi_returns)
        # Missing data → IC = 0
        for period in [1, 2, 5, 10, 20]:
            assert decay[period] == 0.0
