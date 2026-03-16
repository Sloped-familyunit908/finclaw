"""
Overfitting Detection — Deflated Sharpe, CPCV, White's Reality Check, PBO.

Tools to detect whether backtested strategy performance is genuine or
the result of data mining / overfitting.
"""

import math
from typing import Optional

import numpy as np
from scipy import stats as scipy_stats


class OverfitDetector:
    """Static methods for overfitting detection in backtesting."""

    @staticmethod
    def deflated_sharpe_ratio(sharpe: float, n_trials: int,
                               variance: float = 1.0,
                               n_obs: int = 252,
                               skew: float = 0.0,
                               kurtosis: float = 3.0) -> float:
        """
        Deflated Sharpe Ratio (Bailey & López de Prado, 2014).

        Adjusts the Sharpe ratio for the number of trials (strategies tested),
        accounting for the multiple testing bias.

        Args:
            sharpe: Observed Sharpe ratio
            n_trials: Number of strategies/parameter combos tested
            variance: Variance of Sharpe ratios across trials
            n_obs: Number of observations (trading days)
            skew: Skewness of returns
            kurtosis: Kurtosis of returns (3 = normal)

        Returns:
            Probability that the Sharpe ratio is genuine (0-1).
            Values > 0.95 suggest the Sharpe is likely real.
        """
        if n_trials < 1:
            raise ValueError("n_trials must be >= 1")
        if n_obs < 2:
            raise ValueError("n_obs must be >= 2")

        # Expected max Sharpe under null (Euler-Mascheroni approximation)
        euler_mascheroni = 0.5772156649
        e_max_sharpe = math.sqrt(2 * math.log(n_trials)) * (
            1 - euler_mascheroni / (2 * math.log(max(n_trials, 2)))
        ) * math.sqrt(variance)

        # Standard error of Sharpe
        se = math.sqrt(
            (1 - skew * sharpe + ((kurtosis - 1) / 4) * sharpe ** 2) / n_obs
        )

        if se == 0:
            return 1.0 if sharpe > e_max_sharpe else 0.0

        # Z-score
        z = (sharpe - e_max_sharpe) / se

        # Probability
        return float(scipy_stats.norm.cdf(z))

    @staticmethod
    def combinatorial_purged_cv(strategy_fn, data: np.ndarray,
                                 n_splits: int = 10,
                                 purge_pct: float = 0.01) -> dict:
        """
        Combinatorial Purged Cross-Validation (CPCV).

        Tests all C(n_splits, n_splits//2) train/test combinations
        with purging to prevent information leakage.

        Args:
            strategy_fn: Callable(data) -> np.ndarray of returns
            data: Price/return data array
            n_splits: Number of groups to split data into
            purge_pct: Fraction of data to purge at boundaries

        Returns:
            Dict with oos_sharpes, mean_oos_sharpe, pbo (probability of backtest overfitting).
        """
        n = len(data)
        if n < n_splits * 2:
            raise ValueError(f"Need at least {n_splits * 2} data points")

        group_size = n // n_splits
        purge_size = max(1, int(n * purge_pct))

        # Generate groups
        groups = []
        for i in range(n_splits):
            start = i * group_size
            end = start + group_size if i < n_splits - 1 else n
            groups.append((start, end))

        # For efficiency, use a subset of combinations
        from itertools import combinations
        test_size = n_splits // 2
        all_combos = list(combinations(range(n_splits), test_size))

        # Limit to 50 combos for performance
        if len(all_combos) > 50:
            rng = np.random.RandomState(42)
            indices = rng.choice(len(all_combos), 50, replace=False)
            all_combos = [all_combos[i] for i in indices]

        oos_sharpes = []
        is_sharpes = []

        for test_groups in all_combos:
            train_groups = [i for i in range(n_splits) if i not in test_groups]

            # Build train/test arrays with purging
            train_indices = []
            test_indices = []

            for gi in train_groups:
                s, e = groups[gi]
                # Purge boundaries adjacent to test groups
                if gi + 1 in test_groups:
                    e = max(s, e - purge_size)
                if gi - 1 in test_groups:
                    s = min(e, s + purge_size)
                train_indices.extend(range(s, e))

            for gi in test_groups:
                s, e = groups[gi]
                test_indices.extend(range(s, e))

            if not train_indices or not test_indices:
                continue

            train_data = data[train_indices]
            test_data = data[test_indices]

            try:
                is_returns = strategy_fn(train_data)
                oos_returns = strategy_fn(test_data)

                is_std = np.std(is_returns)
                oos_std = np.std(oos_returns)

                is_sharpe = float(np.mean(is_returns) / is_std * math.sqrt(252)) if is_std > 0 else 0.0
                oos_sharpe = float(np.mean(oos_returns) / oos_std * math.sqrt(252)) if oos_std > 0 else 0.0

                is_sharpes.append(is_sharpe)
                oos_sharpes.append(oos_sharpe)
            except Exception:
                continue

        if not oos_sharpes:
            return {'oos_sharpes': [], 'mean_oos_sharpe': 0.0, 'pbo': 1.0}

        # PBO = fraction of combos where OOS Sharpe < 0
        pbo = sum(1 for s in oos_sharpes if s < 0) / len(oos_sharpes)

        return {
            'oos_sharpes': oos_sharpes,
            'is_sharpes': is_sharpes,
            'mean_oos_sharpe': float(np.mean(oos_sharpes)),
            'std_oos_sharpe': float(np.std(oos_sharpes)),
            'pbo': pbo,
            'n_combinations': len(all_combos),
        }

    @staticmethod
    def white_reality_check(strategy_returns: list | np.ndarray,
                            benchmark_returns: list | np.ndarray,
                            n_boot: int = 1000,
                            seed: int = 42) -> dict:
        """
        White's Reality Check (2000) / SPA test.

        Tests whether the strategy's outperformance over the benchmark
        is statistically significant using bootstrap.

        Args:
            strategy_returns: Strategy daily returns
            benchmark_returns: Benchmark daily returns
            n_boot: Number of bootstrap samples
            seed: Random seed

        Returns:
            Dict with p_value, significant (at 5%), mean_excess.
        """
        strat = np.asarray(strategy_returns, dtype=float)
        bench = np.asarray(benchmark_returns, dtype=float)

        min_len = min(len(strat), len(bench))
        if min_len < 10:
            raise ValueError("Need at least 10 return observations")

        strat = strat[:min_len]
        bench = bench[:min_len]

        excess = strat - bench
        observed_stat = np.mean(excess)

        rng = np.random.RandomState(seed)
        boot_stats = np.zeros(n_boot)

        for i in range(n_boot):
            # Stationary bootstrap with block length sqrt(n)
            block_len = max(1, int(math.sqrt(min_len)))
            boot_excess = np.zeros(min_len)
            pos = 0
            while pos < min_len:
                start = rng.randint(0, min_len)
                length = min(block_len, min_len - pos)
                for j in range(length):
                    boot_excess[pos] = excess[(start + j) % min_len]
                    pos += 1
            boot_stats[i] = np.mean(boot_excess)

        # Center the bootstrap distribution
        centered = boot_stats - np.mean(boot_stats)
        p_value = float(np.mean(centered >= observed_stat))

        return {
            'p_value': p_value,
            'significant': p_value < 0.05,
            'mean_excess': float(observed_stat),
            'observed_stat': float(observed_stat),
            'boot_mean': float(np.mean(boot_stats)),
            'boot_std': float(np.std(boot_stats)),
        }

    @staticmethod
    def probability_of_backtest_overfitting(oos_results: list[float]) -> float:
        """
        Probability of Backtest Overfitting (PBO).

        Given a list of out-of-sample performance metrics from CPCV or
        walk-forward, estimates the probability that the strategy is overfit.

        Args:
            oos_results: List of OOS performance values (e.g., Sharpe ratios)

        Returns:
            Probability of overfitting (0-1). Values > 0.5 suggest overfitting.
        """
        if not oos_results:
            return 1.0

        arr = np.asarray(oos_results, dtype=float)
        if len(arr) < 2:
            return 0.0 if arr[0] > 0 else 1.0

        # PBO = fraction of OOS results that are negative
        # (below the median of a random strategy = 0)
        n_negative = np.sum(arr < 0)
        pbo = float(n_negative / len(arr))

        return pbo
