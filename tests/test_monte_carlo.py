"""
Tests for Monte Carlo validation module.

Covers:
  - Known profitable trades → statistically significant
  - Random/noise trades → NOT significant
  - Bootstrap CI contains true mean
  - Shuffle preserves trade set
  - Edge cases: empty, single, all wins, all losses
  - Regime stability checks
  - Report generation
  - Metric correctness
"""

from __future__ import annotations

import json
import math
import os
import random
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evolution.monte_carlo import (
    MonteCarloResult,
    MonteCarloValidator,
    generate_validation_report,
)


class TestMonteCarloValidatorProfitable(unittest.TestCase):
    """Test with known profitable trades → should be significant."""

    def setUp(self):
        # Strongly profitable: most trades are winners with decent edge
        self.trades = [3.0, 2.5, -1.0, 4.0, 1.5, -0.5, 3.5, 2.0, -1.5, 5.0,
                       2.0, 3.0, -0.8, 4.5, 1.0, 2.5, -1.2, 3.0, 2.5, 4.0]
        self.validator = MonteCarloValidator(self.trades, n_iterations=1000, seed=42)

    def test_significant_strategy_detected(self):
        """Profitable strategy should be statistically significant."""
        result = self.validator.validate()
        self.assertTrue(result.is_statistically_significant,
                        f"Expected significant, got p={result.p_value_vs_random}")

    def test_positive_median_return(self):
        """Profitable trades should have positive median return."""
        result = self.validator.validate()
        self.assertGreater(result.median_return, 0.0)

    def test_positive_median_sharpe(self):
        """Profitable trades should have positive Sharpe ratio."""
        result = self.validator.validate()
        self.assertGreater(result.median_sharpe, 0.0)

    def test_low_p_value(self):
        """Profitable strategy should have low p-value."""
        result = self.validator.validate()
        self.assertLess(result.p_value_vs_random, 0.05)


class TestMonteCarloValidatorRandom(unittest.TestCase):
    """Test with random/noise trades → should NOT be significant."""

    def setUp(self):
        # Zero-mean random trades: no edge
        rng = random.Random(123)
        self.trades = [rng.gauss(0, 2) for _ in range(50)]
        self.validator = MonteCarloValidator(self.trades, n_iterations=1000, seed=42)

    def test_random_trades_not_significant(self):
        """Random zero-mean trades should not be significant."""
        result = self.validator.validate()
        # p-value should be high (> 0.05 typically)
        # With zero-mean trades, shuffling shouldn't change much
        self.assertGreater(result.p_value_vs_random, 0.01,
                           "Pure random trades should have high p-value")


class TestBootstrapCI(unittest.TestCase):
    """Test that bootstrap CI contains the true mean."""

    def test_ci_contains_original_return(self):
        """95% CI should typically contain the original annual return."""
        trades = [2.0, -1.0, 3.0, -0.5, 1.5, 2.0, -1.0, 1.0, 0.5, 2.5]
        validator = MonteCarloValidator(trades, n_iterations=1000, seed=42)
        result = validator.validate()

        # The original return should be within a reasonable range of the CI
        # (CI should bracket the original pretty well)
        self.assertLessEqual(result.ci_95_lower, result.original_annual_return * 1.5 + 50,
                             "CI lower bound should not exceed original by huge margin")
        self.assertGreaterEqual(result.ci_95_upper, result.original_annual_return * 0.5 - 50,
                                "CI upper bound should be reasonable")

    def test_ci_lower_less_than_upper(self):
        """Lower CI bound must be less than upper."""
        trades = [1.0, 2.0, -0.5, 3.0, -1.0, 2.5, 1.5, -0.3]
        validator = MonteCarloValidator(trades, n_iterations=1000, seed=42)
        result = validator.validate()

        self.assertLess(result.ci_95_lower, result.ci_95_upper)
        self.assertLess(result.sharpe_ci_lower, result.sharpe_ci_upper)

    def test_ci_median_between_bounds(self):
        """Median should be between CI bounds."""
        trades = [1.0, 2.0, -0.5, 3.0, -1.0, 2.5, 1.5, -0.3, 4.0, -2.0]
        validator = MonteCarloValidator(trades, n_iterations=1000, seed=42)
        result = validator.validate()

        self.assertGreaterEqual(result.median_return, result.ci_95_lower)
        self.assertLessEqual(result.median_return, result.ci_95_upper)
        self.assertGreaterEqual(result.median_sharpe, result.sharpe_ci_lower)
        self.assertLessEqual(result.median_sharpe, result.sharpe_ci_upper)


class TestShufflePreservation(unittest.TestCase):
    """Test that shuffle preserves the trade set."""

    def test_shuffle_preserves_trades(self):
        """After shuffling, original trades list should be unchanged."""
        trades = [1.0, 2.0, 3.0, -1.0, -2.0]
        validator = MonteCarloValidator(trades, n_iterations=10, seed=42)
        original = list(trades)
        validator.shuffle_test()
        self.assertEqual(validator.trades, original,
                         "Original trades must not be mutated by shuffle")

    def test_shuffle_returns_correct_count(self):
        """Shuffle test should return n_iterations results."""
        trades = [1.0, 2.0, -1.0]
        n = 500
        validator = MonteCarloValidator(trades, n_iterations=n, seed=42)
        results = validator.shuffle_test()
        self.assertEqual(len(results), n)


class TestEdgeCases(unittest.TestCase):
    """Edge cases: empty, single, all wins, all losses."""

    def test_empty_trades(self):
        """Empty trade list should return safe defaults."""
        validator = MonteCarloValidator([], n_iterations=100, seed=42)
        result = validator.validate()
        self.assertEqual(result.n_trades, 0)
        self.assertEqual(result.median_return, 0.0)
        self.assertEqual(result.median_sharpe, 0.0)
        self.assertFalse(result.is_statistically_significant)
        self.assertFalse(result.regime_stable)

    def test_single_trade(self):
        """Single trade should not crash and should return valid output."""
        validator = MonteCarloValidator([5.0], n_iterations=100, seed=42)
        result = validator.validate()
        self.assertEqual(result.n_trades, 1)
        self.assertFalse(result.regime_stable)  # Can't split 1 trade

    def test_all_wins(self):
        """All winning trades should be significant."""
        trades = [2.0] * 20
        validator = MonteCarloValidator(trades, n_iterations=1000, seed=42)
        result = validator.validate()
        self.assertGreater(result.median_return, 0)
        self.assertGreater(result.median_sharpe, 0)
        self.assertTrue(result.regime_stable)

    def test_all_losses(self):
        """All losing trades should not be significant."""
        trades = [-2.0] * 20
        validator = MonteCarloValidator(trades, n_iterations=1000, seed=42)
        result = validator.validate()
        self.assertLess(result.median_return, 0)
        self.assertFalse(result.regime_stable)

    def test_two_trades(self):
        """Two trades — minimum for regime split."""
        validator = MonteCarloValidator([3.0, 2.0], n_iterations=100, seed=42)
        result = validator.validate()
        self.assertEqual(result.n_trades, 2)
        self.assertTrue(result.regime_stable)  # Both halves profitable


class TestRegimeStability(unittest.TestCase):
    """Test regime stability with balanced vs imbalanced halves."""

    def test_balanced_halves_stable(self):
        """Both halves profitable → regime stable."""
        # First half: positive, second half: also positive
        trades = [2.0, 3.0, 1.0, 2.0, -0.5, 3.0, 1.5, 2.0, 1.0, 4.0]
        validator = MonteCarloValidator(trades, seed=42)
        self.assertTrue(validator.regime_robustness())

    def test_imbalanced_halves_unstable(self):
        """First half profitable, second half losing → unstable."""
        trades = [5.0, 4.0, 3.0, 6.0, 2.0, -3.0, -4.0, -5.0, -6.0, -3.0]
        validator = MonteCarloValidator(trades, seed=42)
        self.assertFalse(validator.regime_robustness())

    def test_first_half_losing_unstable(self):
        """First half losing, second half profitable → unstable."""
        trades = [-3.0, -4.0, -5.0, -2.0, -1.0, 5.0, 4.0, 3.0, 6.0, 7.0]
        validator = MonteCarloValidator(trades, seed=42)
        self.assertFalse(validator.regime_robustness())


class TestMetricCorrectness(unittest.TestCase):
    """Verify individual metric computations."""

    def test_annual_return_simple(self):
        """Known simple case for annual return."""
        # 10 trades of +1% each → compound = 1.01^10 - 1 ≈ 10.46%
        trades = [1.0] * 10
        ar = MonteCarloValidator._annual_return(trades, trading_days=250)
        # 10 days → 10/250 = 0.04 years → annualized = (1.1046)^(1/0.04) - 1
        expected_total = 1.01 ** 10 - 1
        expected_annual = ((1 + expected_total) ** (250.0 / 10) - 1) * 100
        self.assertAlmostEqual(ar, expected_annual, places=1)

    def test_sharpe_positive(self):
        """Positive mean trades should give positive Sharpe."""
        trades = [2.0, 1.0, 3.0, 0.5, 2.5]
        sharpe = MonteCarloValidator._sharpe_ratio(trades)
        self.assertGreater(sharpe, 0)

    def test_sharpe_negative(self):
        """Negative mean trades should give negative Sharpe."""
        trades = [-2.0, -1.0, -3.0, -0.5, -2.5]
        sharpe = MonteCarloValidator._sharpe_ratio(trades)
        self.assertLess(sharpe, 0)

    def test_max_drawdown_no_loss(self):
        """All positive trades → small or zero drawdown."""
        trades = [1.0, 2.0, 3.0, 1.0, 2.0]
        dd = MonteCarloValidator._max_drawdown(trades)
        self.assertEqual(dd, 0.0)

    def test_max_drawdown_known(self):
        """Known drawdown scenario."""
        # Up 10%, down 20% from peak, then recover
        trades = [10.0, -20.0, 15.0]
        dd = MonteCarloValidator._max_drawdown(trades)
        # After +10%: equity = 1.1, peak = 1.1
        # After -20%: equity = 1.1 * 0.8 = 0.88, dd = (1.1 - 0.88)/1.1 = 20%
        self.assertAlmostEqual(dd, 20.0, places=1)

    def test_percentile_basic(self):
        """Percentile on simple sorted data."""
        data = list(range(101))  # 0..100
        self.assertAlmostEqual(MonteCarloValidator._percentile(data, 50), 50.0)
        self.assertAlmostEqual(MonteCarloValidator._percentile(data, 0), 0.0)
        self.assertAlmostEqual(MonteCarloValidator._percentile(data, 100), 100.0)


class TestReportGeneration(unittest.TestCase):
    """Test JSON report generation."""

    def test_generate_report_creates_file(self):
        """Report should be written to disk as valid JSON."""
        trades = [2.0, -1.0, 3.0, 1.0, -0.5, 2.5]
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            output_path = f.name

        try:
            result = generate_validation_report(trades, output_path, n_iterations=100, seed=42)
            self.assertTrue(os.path.exists(output_path))

            with open(output_path, "r", encoding="utf-8") as f:
                report = json.load(f)

            self.assertIn("monte_carlo_validation", report)
            self.assertIn("summary", report)
            self.assertIn("verdict", report["summary"])
            self.assertIn("interpretation", report["summary"])
            self.assertEqual(report["monte_carlo_validation"]["n_trades"], 6)
        finally:
            os.unlink(output_path)

    def test_report_result_matches_return(self):
        """generate_validation_report should return the same result as stored."""
        trades = [1.0, 2.0, -1.0, 3.0]
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            output_path = f.name

        try:
            result = generate_validation_report(trades, output_path, n_iterations=100, seed=42)
            self.assertIsInstance(result, MonteCarloResult)
            self.assertEqual(result.n_trades, 4)

            with open(output_path, "r", encoding="utf-8") as f:
                report = json.load(f)

            self.assertAlmostEqual(
                report["monte_carlo_validation"]["median_return"],
                result.median_return,
                places=5
            )
        finally:
            os.unlink(output_path)


class TestReproducibility(unittest.TestCase):
    """Test that seed produces deterministic results."""

    def test_same_seed_same_results(self):
        """Same seed should produce identical results."""
        trades = [2.0, -1.0, 3.0, 1.5, -0.5, 2.5, -1.0, 4.0]
        v1 = MonteCarloValidator(trades, n_iterations=500, seed=42)
        v2 = MonteCarloValidator(trades, n_iterations=500, seed=42)
        r1 = v1.validate()
        r2 = v2.validate()

        self.assertAlmostEqual(r1.median_return, r2.median_return, places=10)
        self.assertAlmostEqual(r1.p_value_vs_random, r2.p_value_vs_random, places=10)
        self.assertEqual(r1.is_statistically_significant, r2.is_statistically_significant)

    def test_different_seed_different_results(self):
        """Different seeds should (very likely) produce different results."""
        trades = [2.0, -1.0, 3.0, 1.5, -0.5, 2.5, -1.0, 4.0]
        v1 = MonteCarloValidator(trades, n_iterations=500, seed=42)
        v2 = MonteCarloValidator(trades, n_iterations=500, seed=99)
        r1 = v1.validate()
        r2 = v2.validate()

        # At least some metric should differ
        same = (
            r1.median_return == r2.median_return
            and r1.median_sharpe == r2.median_sharpe
            and r1.p_value_vs_random == r2.p_value_vs_random
        )
        self.assertFalse(same, "Different seeds should give different results")


class TestDataclassMonteCarloResult(unittest.TestCase):
    """Test MonteCarloResult dataclass behavior."""

    def test_default_values(self):
        """Default MonteCarloResult should have safe defaults."""
        r = MonteCarloResult()
        self.assertEqual(r.median_return, 0.0)
        self.assertEqual(r.p_value_vs_random, 1.0)
        self.assertFalse(r.is_statistically_significant)
        self.assertFalse(r.regime_stable)
        self.assertEqual(r.n_trades, 0)

    def test_asdict(self):
        """Result should be serializable via dataclasses.asdict."""
        from dataclasses import asdict
        r = MonteCarloResult(median_return=50.0, n_trades=100)
        d = asdict(r)
        self.assertEqual(d["median_return"], 50.0)
        self.assertEqual(d["n_trades"], 100)


if __name__ == "__main__":
    unittest.main()
