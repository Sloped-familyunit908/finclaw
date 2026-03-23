"""
Monte Carlo Simulation & Bootstrap Confidence Intervals for strategy validation.

Validates trading strategy robustness using:
  - Shuffle test: randomly reorder trades to test path-dependency
  - Bootstrap confidence intervals: resample with replacement for CI estimation
  - Regime robustness: verify profitability across different market regimes

Uses only Python stdlib (random, math, statistics) — no numpy dependency.
"""

from __future__ import annotations

import json
import math
import random
import statistics
from dataclasses import asdict, dataclass, field
from typing import List, Optional


@dataclass
class MonteCarloResult:
    """Results from Monte Carlo validation."""

    # Annual return distribution
    median_return: float = 0.0
    ci_95_lower: float = 0.0
    ci_95_upper: float = 0.0

    # Sharpe ratio distribution
    median_sharpe: float = 0.0
    sharpe_ci_lower: float = 0.0
    sharpe_ci_upper: float = 0.0

    # Max drawdown distribution
    median_drawdown: float = 0.0
    drawdown_ci_lower: float = 0.0
    drawdown_ci_upper: float = 0.0

    # Statistical significance
    p_value_vs_random: float = 1.0
    is_statistically_significant: bool = False

    # Regime stability
    regime_stable: bool = False

    # Extra info
    n_trades: int = 0
    n_iterations: int = 0
    original_annual_return: float = 0.0
    original_sharpe: float = 0.0
    original_max_drawdown: float = 0.0


class MonteCarloValidator:
    """Validate trading strategy robustness with Monte Carlo methods.

    Args:
        trades: List of per-trade return percentages (e.g. [2.5, -1.3, 0.8, ...]).
        n_iterations: Number of Monte Carlo iterations (default 1000).
        seed: Random seed for reproducibility (default None).
        trading_days_per_year: Trading days per year (default 250).
    """

    def __init__(
        self,
        trades: List[float],
        n_iterations: int = 1000,
        seed: Optional[int] = None,
        trading_days_per_year: int = 250,
    ):
        self.trades = list(trades)
        self.n_iterations = n_iterations
        self.trading_days_per_year = trading_days_per_year
        self.rng = random.Random(seed)

    # ── Core metrics ────────────────────────────────────────────────

    @staticmethod
    def _annual_return(trades: List[float], trading_days: int = 250) -> float:
        """Compute annualized return from a sequence of trade returns (%).

        Compounds trade returns, then annualizes based on how many
        trading days the full trade set would span.
        """
        if not trades:
            return 0.0
        equity = 1.0
        for t in trades:
            equity *= (1 + t / 100.0)
        total_return = equity - 1.0
        # Assume each trade takes ~1 day (approximation for annualization)
        n_days = len(trades)
        years = n_days / trading_days if trading_days > 0 else 1.0
        if years <= 0:
            years = 1.0
        if total_return <= -1.0:
            return -100.0
        return ((1 + total_return) ** (1 / years) - 1) * 100.0

    @staticmethod
    def _sharpe_ratio(trades: List[float], risk_free_annual: float = 0.0) -> float:
        """Compute annualized Sharpe ratio from trade returns (%).

        Uses daily-return approximation: Sharpe = mean/std * sqrt(250).
        """
        if len(trades) < 2:
            return 0.0
        mean_ret = statistics.mean(trades)
        std_ret = statistics.stdev(trades)
        if std_ret == 0:
            return 0.0 if mean_ret == 0 else (10.0 if mean_ret > 0 else -10.0)
        # Annualize: assume each trade ≈ 1 day
        daily_sharpe = (mean_ret - risk_free_annual / 250.0) / std_ret
        return daily_sharpe * math.sqrt(250)

    @staticmethod
    def _max_drawdown(trades: List[float]) -> float:
        """Compute maximum drawdown (%) from a sequence of trade returns (%).

        Returns a positive number (e.g. 15.0 means 15% drawdown).
        """
        if not trades:
            return 0.0
        equity = 1.0
        peak = 1.0
        max_dd = 0.0
        for t in trades:
            equity *= (1 + t / 100.0)
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak * 100.0 if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
        return max_dd

    # ── Shuffle test ────────────────────────────────────────────────

    def shuffle_test(self) -> List[float]:
        """Randomly shuffle trade order N times, compute annual return each time.

        Returns list of annual returns from shuffled sequences.
        """
        if not self.trades:
            return []
        results = []
        for _ in range(self.n_iterations):
            shuffled = list(self.trades)
            self.rng.shuffle(shuffled)
            ar = self._annual_return(shuffled, self.trading_days_per_year)
            results.append(ar)
        return results

    # ── Bootstrap ───────────────────────────────────────────────────

    def bootstrap(self) -> tuple:
        """Bootstrap resample with replacement N times.

        Returns:
            (annual_returns, sharpes, max_drawdowns) — each a list of length n_iterations.
        """
        if not self.trades:
            return [], [], []

        n = len(self.trades)
        annual_returns = []
        sharpes = []
        drawdowns = []

        for _ in range(self.n_iterations):
            sample = [self.trades[self.rng.randint(0, n - 1)] for _ in range(n)]
            annual_returns.append(self._annual_return(sample, self.trading_days_per_year))
            sharpes.append(self._sharpe_ratio(sample))
            drawdowns.append(self._max_drawdown(sample))

        return annual_returns, sharpes, drawdowns

    # ── Regime robustness ───────────────────────────────────────────

    def regime_robustness(self) -> bool:
        """Split trades into first half and second half; both must be profitable.

        Returns True if both halves have positive total return.
        """
        if len(self.trades) < 2:
            return False
        mid = len(self.trades) // 2
        first_half = self.trades[:mid]
        second_half = self.trades[mid:]

        def _is_profitable(t: List[float]) -> bool:
            equity = 1.0
            for r in t:
                equity *= (1 + r / 100.0)
            return equity > 1.0

        return _is_profitable(first_half) and _is_profitable(second_half)

    # ── P-value vs random ───────────────────────────────────────────

    def p_value_vs_random(self) -> float:
        """Compute p-value: probability that random (zero-mean) trading
        produces same or better annual return.

        Null hypothesis: trades are drawn from a zero-mean distribution
        with the same volatility as the actual trades.  We generate
        random trade sequences by flipping the sign of each trade with
        50% probability (sign-randomization test).  This preserves
        magnitude but destroys any directional edge.
        """
        if not self.trades:
            return 1.0
        original_return = self._annual_return(self.trades, self.trading_days_per_year)
        count_better = 0
        for _ in range(self.n_iterations):
            randomized = [
                t if self.rng.random() >= 0.5 else -t
                for t in self.trades
            ]
            rand_return = self._annual_return(randomized, self.trading_days_per_year)
            if rand_return >= original_return:
                count_better += 1
        return count_better / self.n_iterations

    # ── Percentile helper ───────────────────────────────────────────

    @staticmethod
    def _percentile(data: List[float], pct: float) -> float:
        """Compute percentile using linear interpolation (like numpy)."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        n = len(sorted_data)
        k = (pct / 100.0) * (n - 1)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_data[int(k)]
        d0 = sorted_data[f]
        d1 = sorted_data[c]
        return d0 + (d1 - d0) * (k - f)

    # ── Full validation ─────────────────────────────────────────────

    def validate(self) -> MonteCarloResult:
        """Run full Monte Carlo validation suite.

        Returns MonteCarloResult with all metrics, CIs, and significance tests.
        """
        result = MonteCarloResult(
            n_trades=len(self.trades),
            n_iterations=self.n_iterations,
        )

        if not self.trades:
            return result

        # Original metrics
        result.original_annual_return = self._annual_return(
            self.trades, self.trading_days_per_year
        )
        result.original_sharpe = self._sharpe_ratio(self.trades)
        result.original_max_drawdown = self._max_drawdown(self.trades)

        # Bootstrap confidence intervals
        boot_returns, boot_sharpes, boot_drawdowns = self.bootstrap()

        if boot_returns:
            result.median_return = self._percentile(boot_returns, 50)
            result.ci_95_lower = self._percentile(boot_returns, 2.5)
            result.ci_95_upper = self._percentile(boot_returns, 97.5)

        if boot_sharpes:
            result.median_sharpe = self._percentile(boot_sharpes, 50)
            result.sharpe_ci_lower = self._percentile(boot_sharpes, 2.5)
            result.sharpe_ci_upper = self._percentile(boot_sharpes, 97.5)

        if boot_drawdowns:
            result.median_drawdown = self._percentile(boot_drawdowns, 50)
            result.drawdown_ci_lower = self._percentile(boot_drawdowns, 2.5)
            result.drawdown_ci_upper = self._percentile(boot_drawdowns, 97.5)

        # P-value vs random (shuffle test)
        result.p_value_vs_random = self.p_value_vs_random()
        result.is_statistically_significant = result.p_value_vs_random < 0.05

        # Regime robustness
        result.regime_stable = self.regime_robustness()

        return result


def generate_validation_report(
    trades: List[float],
    output_path: str,
    n_iterations: int = 1000,
    seed: Optional[int] = None,
) -> MonteCarloResult:
    """Generate a full Monte Carlo validation report.

    Args:
        trades: List of per-trade return percentages.
        output_path: Path to write JSON report.
        n_iterations: Number of Monte Carlo iterations.
        seed: Random seed for reproducibility.

    Returns:
        MonteCarloResult with all validation metrics.
    """
    validator = MonteCarloValidator(
        trades, n_iterations=n_iterations, seed=seed
    )
    result = validator.validate()

    # Build report
    report = {
        "monte_carlo_validation": asdict(result),
        "summary": _build_summary(result),
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return result


def _build_summary(result: MonteCarloResult) -> dict:
    """Build human-readable summary from MonteCarloResult."""
    significance = (
        "✅ SIGNIFICANT"
        if result.is_statistically_significant
        else "❌ NOT SIGNIFICANT"
    )
    regime = "✅ STABLE" if result.regime_stable else "⚠️ UNSTABLE"

    return {
        "verdict": significance,
        "annual_return": (
            f"{result.median_return:.1f}% "
            f"(95% CI: {result.ci_95_lower:.1f}% to {result.ci_95_upper:.1f}%)"
        ),
        "sharpe_ratio": (
            f"{result.median_sharpe:.2f} "
            f"(95% CI: {result.sharpe_ci_lower:.2f} to {result.sharpe_ci_upper:.2f})"
        ),
        "max_drawdown": (
            f"{result.median_drawdown:.1f}% "
            f"(95% CI: {result.drawdown_ci_lower:.1f}% to {result.drawdown_ci_upper:.1f}%)"
        ),
        "p_value": f"{result.p_value_vs_random:.4f}",
        "regime_stability": regime,
        "n_trades": result.n_trades,
        "n_iterations": result.n_iterations,
        "interpretation": (
            f"Strategy with {result.n_trades} trades. "
            f"Median annual return {result.median_return:.1f}% "
            f"(p={result.p_value_vs_random:.4f}). "
            f"Statistical significance: {significance}. "
            f"Regime stability: {regime}."
        ),
    }
