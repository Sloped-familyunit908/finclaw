"""Financial-aware data splitting strategies."""

import math
from itertools import combinations


class FinancialDataSplitter:
    """Data splitting utilities that respect temporal ordering and avoid look-ahead bias."""

    @staticmethod
    def time_series_split(data: list, n_splits: int = 5, gap: int = 5) -> list[tuple[list[int], list[int]]]:
        """Expanding window time series split with gap between train and test.

        Args:
            data: Input data (list of observations).
            n_splits: Number of train/test splits.
            gap: Number of observations to skip between train and test.

        Returns:
            List of (train_indices, test_indices) tuples.
        """
        n = len(data)
        if n < n_splits + gap + 1:
            raise ValueError(f"Not enough data ({n}) for {n_splits} splits with gap={gap}")

        test_size = max(1, (n - gap) // (n_splits + 1))
        splits = []

        for i in range(n_splits):
            test_start = (i + 1) * test_size + gap
            test_end = min(test_start + test_size, n)
            if test_start >= n:
                break
            train_end = test_start - gap
            if train_end <= 0:
                continue
            train_idx = list(range(train_end))
            test_idx = list(range(test_start, test_end))
            if train_idx and test_idx:
                splits.append((train_idx, test_idx))

        return splits

    @staticmethod
    def purged_kfold(data: list, n_splits: int = 5, embargo_pct: float = 0.01) -> list[tuple[list[int], list[int]]]:
        """Purged K-Fold cross-validation.

        Removes training observations that overlap with test period,
        plus an embargo period after each test fold.

        Args:
            data: Input data.
            n_splits: Number of folds.
            embargo_pct: Fraction of data to embargo after test set.

        Returns:
            List of (train_indices, test_indices) tuples.
        """
        n = len(data)
        if n < n_splits:
            raise ValueError(f"Not enough data ({n}) for {n_splits} splits")

        embargo = max(1, int(n * embargo_pct))
        fold_size = n // n_splits
        splits = []

        for i in range(n_splits):
            test_start = i * fold_size
            test_end = min(test_start + fold_size, n) if i < n_splits - 1 else n

            test_idx = list(range(test_start, test_end))

            # Purge: remove train samples that are too close to test
            purge_start = max(0, test_start - embargo)
            purge_end = min(n, test_end + embargo)

            train_idx = [j for j in range(n) if j < purge_start or j >= purge_end]

            if train_idx and test_idx:
                splits.append((train_idx, test_idx))

        return splits

    @staticmethod
    def combinatorial_purged(data: list, n_splits: int = 6,
                             n_test_splits: int = 2) -> list[tuple[list[int], list[int]]]:
        """Combinatorial Purged Cross-Validation (CPCV).

        Generates all combinations of test groups, using remaining as train.
        More paths = more robust backtest evaluation.

        Args:
            data: Input data.
            n_splits: Total number of groups to divide data into.
            n_test_splits: Number of groups to use as test in each combination.

        Returns:
            List of (train_indices, test_indices) tuples.
        """
        n = len(data)
        if n < n_splits:
            raise ValueError(f"Not enough data ({n}) for {n_splits} splits")
        if n_test_splits >= n_splits:
            raise ValueError("n_test_splits must be less than n_splits")

        group_size = n // n_splits
        groups = []
        for i in range(n_splits):
            start = i * group_size
            end = start + group_size if i < n_splits - 1 else n
            groups.append(list(range(start, end)))

        splits = []
        for test_combo in combinations(range(n_splits), n_test_splits):
            test_idx = []
            for g in test_combo:
                test_idx.extend(groups[g])
            train_idx = []
            for g in range(n_splits):
                if g not in test_combo:
                    train_idx.extend(groups[g])
            if train_idx and test_idx:
                splits.append((sorted(train_idx), sorted(test_idx)))

        return splits
