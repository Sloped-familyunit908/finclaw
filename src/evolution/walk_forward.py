"""Walk-forward validation for strategy evolution.

Replaces the single 70/30 train/val split with multi-window anchored
walk-forward validation.  Forces strategies to generalise across
multiple unseen time regimes.

A **purged embargo gap** between train and test prevents
indicator-lookback leakage.

Usage (standalone)::

    from src.evolution.walk_forward import WalkForwardValidator, WalkForwardConfig

    cfg = WalkForwardConfig(n_windows=4, embargo_periods=48)
    validator = WalkForwardValidator(cfg)

    # run_backtest_fn(day_start, day_end) -> backtest result tuple
    result = validator.validate(run_backtest_fn, total_bars=8760, warmup=60)
    print(result.final_fitness, result.is_likely_overfit())
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class WalkForwardConfig:
    """Configuration for walk-forward validation.

    Attributes:
        n_windows: Number of OOS test windows.
        min_train_pct: Minimum training data as fraction of total usable bars.
        test_window_pct: Each test window as fraction of total usable bars.
        embargo_periods: Gap between train end and test start (bars).
        warmup_periods: Indicator warmup before first trade (bars).
        oos_weight: Weight for out-of-sample fitness component.
        is_weight: Weight for in-sample fitness component.
        overfit_penalty_threshold: Penalize when OOS/IS ratio falls below this.
        overfit_penalty_factor: Multiply fitness by this on overfit detection.
        min_trades_per_window: Minimum trades in an OOS window to count it.
        use_consistency_weighting: Whether to weight by OOS consistency.
    """

    n_windows: int = 4
    min_train_pct: float = 0.40
    test_window_pct: float = 0.10
    embargo_periods: int = 48
    warmup_periods: int = 60
    oos_weight: float = 0.70
    is_weight: float = 0.30
    overfit_penalty_threshold: float = 0.25
    overfit_penalty_factor: float = 0.20
    min_trades_per_window: int = 10
    use_consistency_weighting: bool = True


# ---------------------------------------------------------------------------
# Result data-classes
# ---------------------------------------------------------------------------

@dataclass
class WindowResult:
    """Results from one walk-forward window."""

    window_index: int
    train_range: Tuple[int, int]
    test_range: Tuple[int, int]
    is_fitness: float
    oos_fitness: float
    oos_annual_return: float
    oos_max_drawdown: float
    oos_sharpe: float
    oos_trades: int
    oos_win_rate: float


@dataclass
class WalkForwardResult:
    """Aggregated walk-forward validation result."""

    final_fitness: float
    is_mean_fitness: float
    oos_mean_fitness: float
    overfit_ratio: float  # oos_mean / is_mean — <1.0 suggests overfit
    consistency_score: float  # 1.0 = identical across windows
    window_results: List[WindowResult] = field(default_factory=list)
    n_valid_windows: int = 0

    def is_likely_overfit(self) -> bool:
        """Return *True* when OOS performance is far below IS performance."""
        return self.overfit_ratio < 0.3


# ---------------------------------------------------------------------------
# Fitness helper (local, mirrors compute_fitness from auto_evolve)
# ---------------------------------------------------------------------------

def _compute_window_fitness(
    annual_return: float,
    max_drawdown: float,
    win_rate: float,
    sharpe: float,
    total_trades: int,
    sortino: float = 0.0,
    max_consec_losses: int = 0,
    monthly_returns: Optional[List[float]] = None,
    positions_used: int = 1,
    max_positions: int = 1,
    avg_turnover: float = 0.0,
) -> float:
    """Lightweight fitness computation for a single window.

    Mirrors the logic of ``compute_fitness`` in *auto_evolve.py* so that
    the walk-forward module stays self-contained.
    """
    dd_denom = max(max_drawdown, 5.0)
    win_factor = math.sqrt(max(win_rate, 0.0))
    sharpe_bonus = 1.0 + max(sharpe, 0.0) * 0.2

    if total_trades < 10:
        trade_penalty = 0.1
    elif total_trades < 30:
        trade_penalty = total_trades / 30.0
    else:
        trade_penalty = 1.0

    base = annual_return * win_factor / dd_denom * sharpe_bonus * trade_penalty

    sortino_bonus = 1.1 if (sortino > sharpe) else 1.0

    if max_consec_losses > 15:
        consec_penalty = 0.4
    elif max_consec_losses > 10:
        consec_penalty = 0.7
    else:
        consec_penalty = 1.0

    consistency_bonus = 1.0
    if monthly_returns and len(monthly_returns) >= 3:
        mean_mr = sum(monthly_returns) / len(monthly_returns)
        if mean_mr != 0:
            var_mr = sum((r - mean_mr) ** 2 for r in monthly_returns) / len(monthly_returns)
            std_mr = math.sqrt(var_mr)
            cv = abs(std_mr / mean_mr)
            if cv < 1.0:
                consistency_bonus = 1.2

    div_bonus = 1.0
    if positions_used >= 2:
        if max_positions >= 5 and positions_used >= 3:
            div_bonus = 1.25
        elif max_positions >= 3 and positions_used >= 2:
            div_bonus = 1.15

    turnover_penalty = 1.0
    if avg_turnover > 0.8:
        turnover_penalty = 0.85
    elif avg_turnover > 0.5:
        turnover_penalty = 0.95

    return (base * sortino_bonus * consec_penalty
            * consistency_bonus * div_bonus * turnover_penalty)


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class WalkForwardValidator:
    """Run anchored walk-forward validation on a strategy.

    The validator is decoupled from :class:`AutoEvolver` — it only needs a
    callable ``run_backtest_fn(day_start, day_end)`` that returns the
    standard 12-element backtest result tuple.
    """

    def __init__(self, config: Optional[WalkForwardConfig] = None) -> None:
        self.config = config or WalkForwardConfig()

    # ---- window computation ------------------------------------------------

    def compute_windows(self, total_bars: int) -> List[Dict[str, Tuple[int, int]]]:
        """Calculate train / embargo / test boundaries.

        Windows are built **back-to-front** from the end of the data and then
        reversed into chronological order.  Training always starts at
        ``warmup_periods`` (anchored / expanding window).

        Returns a list of dicts, each with ``"train"`` and ``"test"`` keys
        whose values are ``(start, end)`` bar indices.
        """
        cfg = self.config
        usable = total_bars - cfg.warmup_periods
        if usable <= 0:
            return []

        test_size = int(usable * cfg.test_window_pct)
        if test_size < 1:
            return []

        windows: List[Dict[str, Tuple[int, int]]] = []

        for i in range(cfg.n_windows):
            test_end = total_bars - i * test_size
            test_start = test_end - test_size
            train_end = test_start - cfg.embargo_periods
            train_start = cfg.warmup_periods

            # Need enough training data
            if train_end - train_start < cfg.warmup_periods * 2:
                break

            # Minimum train fraction check
            if (train_end - train_start) / usable < cfg.min_train_pct:
                break

            windows.append({
                "train": (train_start, train_end),
                "test": (test_start, test_end),
            })

        windows.reverse()  # chronological order
        return windows

    # ---- validation --------------------------------------------------------

    def validate(
        self,
        run_backtest_fn: Callable[..., Tuple],
        total_bars: int,
        warmup: int = 60,
        compute_fitness_fn: Optional[Callable[..., float]] = None,
    ) -> WalkForwardResult:
        """Run full walk-forward validation.

        Args:
            run_backtest_fn: ``(day_start, day_end) -> 12-element tuple``
                matching the signature of ``_run_backtest`` in *auto_evolve.py*.
            total_bars: Length of the price series.
            warmup: Indicator warmup periods (overrides config if provided
                explicitly to the *AutoEvolver* caller; defaults to config
                value).
            compute_fitness_fn: Optional custom fitness function.  When
                ``None``, the built-in :func:`_compute_window_fitness` is used.

        Returns:
            :class:`WalkForwardResult` with aggregated metrics.
        """
        # Allow caller to override warmup via config
        if warmup != 60:
            self.config.warmup_periods = warmup

        fitness_fn = compute_fitness_fn or _compute_window_fitness

        windows = self.compute_windows(total_bars)

        if not windows:
            return WalkForwardResult(
                final_fitness=-1.0,
                is_mean_fitness=0.0,
                oos_mean_fitness=0.0,
                overfit_ratio=0.0,
                consistency_score=0.0,
                n_valid_windows=0,
            )

        window_results: List[WindowResult] = []
        is_fitnesses: List[float] = []
        oos_fitnesses: List[float] = []

        for idx, w in enumerate(windows):
            # --- In-sample: last 30% of train segment ---
            train_start, train_end = w["train"]
            is_seg_start = train_start + int((train_end - train_start) * 0.7)
            is_result = run_backtest_fn(is_seg_start, train_end)
            is_fitness = fitness_fn(
                is_result[0], is_result[1], is_result[2], is_result[3],
                is_result[5],
                sortino=is_result[7],
                max_consec_losses=is_result[8],
                monthly_returns=is_result[9],
                positions_used=is_result[10],
                avg_turnover=is_result[11],
            )

            # --- Out-of-sample ---
            test_start, test_end = w["test"]
            oos_result = run_backtest_fn(test_start, test_end)
            oos_fitness = fitness_fn(
                oos_result[0], oos_result[1], oos_result[2], oos_result[3],
                oos_result[5],
                sortino=oos_result[7],
                max_consec_losses=oos_result[8],
                monthly_returns=oos_result[9],
                positions_used=oos_result[10],
                avg_turnover=oos_result[11],
            )

            wr = WindowResult(
                window_index=idx,
                train_range=(train_start, train_end),
                test_range=(test_start, test_end),
                is_fitness=is_fitness,
                oos_fitness=oos_fitness,
                oos_annual_return=oos_result[0],
                oos_max_drawdown=oos_result[1],
                oos_sharpe=oos_result[3],
                oos_trades=oos_result[5],
                oos_win_rate=oos_result[2],
            )
            window_results.append(wr)
            is_fitnesses.append(is_fitness)
            oos_fitnesses.append(oos_fitness)

        # --- Aggregate ---
        cfg = self.config

        # Filter windows with enough trades
        valid_indices = [
            i for i, wr in enumerate(window_results)
            if wr.oos_trades >= cfg.min_trades_per_window
        ]
        valid_oos = [oos_fitnesses[i] for i in valid_indices]

        if not valid_oos:
            return WalkForwardResult(
                final_fitness=-1.0,
                is_mean_fitness=sum(is_fitnesses) / len(is_fitnesses) if is_fitnesses else 0.0,
                oos_mean_fitness=0.0,
                overfit_ratio=0.0,
                consistency_score=0.0,
                window_results=window_results,
                n_valid_windows=0,
            )

        mean_oos = sum(valid_oos) / len(valid_oos)

        # Consistency weighting
        consistency_score = 1.0
        if cfg.use_consistency_weighting and len(valid_oos) >= 2:
            if mean_oos != 0:
                var_oos = sum((f - mean_oos) ** 2 for f in valid_oos) / len(valid_oos)
                std_oos = math.sqrt(var_oos)
                cv = std_oos / abs(mean_oos)
                consistency_score = max(0.5, 1.0 - cv * 0.3)
            else:
                consistency_score = 0.5

        aggregated_oos = mean_oos * consistency_score

        # IS aggregation
        aggregated_is = sum(is_fitnesses) / len(is_fitnesses) if is_fitnesses else 0.0

        # Combined fitness
        fitness = cfg.oos_weight * aggregated_oos + cfg.is_weight * aggregated_is

        # Overfit penalty
        overfit_ratio = 0.0
        if aggregated_is > 0:
            overfit_ratio = aggregated_oos / aggregated_is
            if overfit_ratio < cfg.overfit_penalty_threshold:
                fitness *= cfg.overfit_penalty_factor
        elif aggregated_is == 0 and aggregated_oos > 0:
            overfit_ratio = 1.0  # IS was zero but OOS positive — not overfit
        # else both zero → ratio stays 0

        return WalkForwardResult(
            final_fitness=fitness,
            is_mean_fitness=aggregated_is,
            oos_mean_fitness=mean_oos,
            overfit_ratio=overfit_ratio,
            consistency_score=consistency_score,
            window_results=window_results,
            n_valid_windows=len(valid_oos),
        )


# ---------------------------------------------------------------------------
# Deflated Sharpe Ratio
# ---------------------------------------------------------------------------

def deflated_sharpe_ratio(
    observed_sharpe: float,
    n_trials: int,
    n_observations: int,
    skew: float = 0.0,
    kurtosis: float = 3.0,
) -> float:
    """Bailey & López de Prado (2014) deflated Sharpe ratio.

    Returns the probability that the *observed* Sharpe ratio is above zero
    after correcting for multiple testing (the number of strategy variants
    tried).

    Args:
        observed_sharpe: The best Sharpe ratio observed.
        n_trials: Total number of independent strategies tested
            (e.g. ``population_size * generations``).
        n_observations: Number of return observations used to compute
            the Sharpe ratio.
        skew: Skewness of the return distribution (0 for normal).
        kurtosis: Kurtosis of the return distribution (3 for normal).

    Returns:
        Probability in ``[0, 1]``.  Values below ~0.95 suggest the
        observed Sharpe may be a statistical artefact.
    """
    if n_trials <= 0 or n_observations <= 1:
        return 0.0

    # Expected maximum Sharpe under the null (all strategies have SR = 0)
    # E[max(Z_1..Z_N)] ≈ (1 - γ/ln(N)) * sqrt(2*ln(N))  (Euler-Mascheroni γ)
    euler_mascheroni = 0.5772156649
    ln_n = math.log(max(n_trials, 2))
    expected_max_sr = (
        (1.0 - euler_mascheroni / ln_n) * math.sqrt(2.0 * ln_n)
        - euler_mascheroni / math.sqrt(2.0 * ln_n)
    )

    # Standard error of the Sharpe ratio (adjusted for skew & kurtosis)
    se_sr = math.sqrt(
        (1.0
         - skew * observed_sharpe
         + ((kurtosis - 1.0) / 4.0) * observed_sharpe ** 2)
        / max(n_observations - 1, 1)
    )

    if se_sr <= 0:
        return 1.0 if observed_sharpe > expected_max_sr else 0.0

    # Test statistic: how far is the observed SR above the expected max?
    t_stat = (observed_sharpe - expected_max_sr) / se_sr

    # Approximate the standard-normal CDF using the logistic approximation
    # Φ(x) ≈ 1 / (1 + e^{-1.7 * x})  (accurate to ~0.01)
    prob = 1.0 / (1.0 + math.exp(-1.7 * t_stat))
    return prob
