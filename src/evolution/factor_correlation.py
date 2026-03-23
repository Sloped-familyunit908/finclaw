"""
Factor Correlation Analyzer
============================
Computes cross-sectional correlation between all factors in the registry,
identifies redundant factor clusters, and recommends a pruned factor list.

Usage:
    from src.evolution.factor_correlation import FactorCorrelationAnalyzer
    analyzer = FactorCorrelationAnalyzer(data, factor_registry)
    analyzer.compute(sample_stocks=50, sample_dates=100)
    redundant = analyzer.get_redundant_pairs()
    pruned = analyzer.get_pruned_factor_list(all_factors)
    analyzer.save_correlation_matrix("evolution_results/factor_correlation.json")
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dataclasses import dataclass, field


@dataclass
class ClusterInfo:
    """Information about a redundant factor cluster."""
    cluster_id: int
    members: List[str]
    representative: str  # factor to keep


class FactorCorrelationAnalyzer:
    """Analyze pairwise Pearson correlation between all dynamic factors.

    Given stock data and a factor registry (same format as auto_evolve.py),
    computes each factor's cross-sectional scores over a sample of stocks
    and dates, then builds the full NxN correlation matrix.
    """

    def __init__(
        self,
        data: Dict[str, Dict[str, list]],
        factor_registry: Any,
        ic_scores: Optional[Dict[str, float]] = None,
        correlation_threshold: float = 0.7,
        seed: int = 42,
    ):
        """
        Args:
            data: Stock data dict {code: {"close": [...], "high": [...], ...}}
            factor_registry: FactorRegistry instance with .factors and .list_factors()
            ic_scores: Optional dict {factor_name: IC} for choosing cluster representatives
            correlation_threshold: Threshold above which factors are considered redundant
            seed: Random seed for sampling
        """
        self.data = data
        self.registry = factor_registry
        self.ic_scores = ic_scores or {}
        self.threshold = correlation_threshold
        self.seed = seed

        # Populated after compute()
        self.correlation_matrix: Dict[str, Dict[str, float]] = {}
        self._redundant_pairs: List[Tuple[str, str, float]] = []
        self._clusters: List[ClusterInfo] = []
        self._computed = False

    def compute(
        self,
        sample_stocks: int = 50,
        sample_dates: int = 100,
    ) -> None:
        """Compute the full factor correlation matrix.

        1. Sample up to ``sample_stocks`` stocks and ``sample_dates`` dates.
        2. For each factor, compute its score across all (stock, date) pairs
           to form a cross-sectional score vector.
        3. Compute Pearson correlation between every pair of factor vectors.
        4. Identify redundant pairs and clusters.

        Args:
            sample_stocks: Max number of stocks to sample
            sample_dates: Max number of dates to sample
        """
        factor_names = self.registry.list_factors()
        if not factor_names:
            self._computed = True
            return

        rng = random.Random(self.seed)

        # Sample stocks
        codes = list(self.data.keys())
        if len(codes) > sample_stocks:
            codes = rng.sample(codes, sample_stocks)

        # Find common date range — use minimum length across sampled stocks
        min_len = min(len(self.data[c]["close"]) for c in codes) if codes else 0
        if min_len < 30:
            # Not enough data — skip
            self._computed = True
            return

        # Sample date indices (avoid first 30 for indicator warmup)
        warmup = 30
        available_days = list(range(warmup, min_len))
        if len(available_days) > sample_dates:
            date_indices = sorted(rng.sample(available_days, sample_dates))
        else:
            date_indices = available_days

        # Build score vectors: factor_name -> list of scores (one per stock-date pair)
        score_vectors: Dict[str, List[float]] = {fn: [] for fn in factor_names}

        for code in codes:
            sd = self.data[code]
            closes = sd["close"]
            highs = sd.get("high", closes)
            lows = sd.get("low", closes)
            volumes = sd.get("volume", [1_000_000] * len(closes))

            for day_idx in date_indices:
                if day_idx >= len(closes):
                    continue
                for fname in factor_names:
                    factor_meta = self.registry.factors.get(fname)
                    if factor_meta is None:
                        score_vectors[fname].append(0.5)
                        continue
                    try:
                        val = factor_meta.compute_fn(closes, highs, lows, volumes, day_idx)
                        val = max(0.0, min(1.0, float(val)))
                        if math.isnan(val) or math.isinf(val):
                            val = 0.5
                    except Exception:
                        val = 0.5
                    score_vectors[fname].append(val)

        # Compute Pearson correlation matrix
        self.correlation_matrix = {}
        for i, f1 in enumerate(factor_names):
            self.correlation_matrix[f1] = {}
            for j, f2 in enumerate(factor_names):
                if i == j:
                    self.correlation_matrix[f1][f2] = 1.0
                elif j < i and f2 in self.correlation_matrix and f1 in self.correlation_matrix[f2]:
                    # Symmetric — reuse already computed value
                    self.correlation_matrix[f1][f2] = self.correlation_matrix[f2][f1]
                else:
                    corr = _pearson_correlation(score_vectors[f1], score_vectors[f2])
                    self.correlation_matrix[f1][f2] = corr

        # Identify redundant pairs
        self._redundant_pairs = []
        for i, f1 in enumerate(factor_names):
            for j, f2 in enumerate(factor_names):
                if j <= i:
                    continue
                corr = self.correlation_matrix[f1][f2]
                if abs(corr) > self.threshold:
                    self._redundant_pairs.append((f1, f2, round(corr, 4)))

        # Sort by descending absolute correlation
        self._redundant_pairs.sort(key=lambda x: abs(x[2]), reverse=True)

        # Build clusters using union-find
        self._clusters = self._build_clusters(factor_names)

        self._computed = True

    def get_redundant_pairs(self) -> List[Tuple[str, str, float]]:
        """Return pairs of factors with abs(correlation) > threshold.

        Returns:
            List of (factor1, factor2, correlation) tuples sorted by |corr| desc.
        """
        if not self._computed:
            raise RuntimeError("Call compute() first")
        return list(self._redundant_pairs)

    def get_pruned_factor_list(self, all_factors: List[str]) -> List[str]:
        """Return a de-duplicated factor list, keeping only cluster representatives.

        For each redundant cluster, keeps the factor with highest standalone IC
        (if IC scores are available), otherwise keeps the first factor alphabetically.

        Args:
            all_factors: Full list of factor names

        Returns:
            Pruned list with redundant factors removed.
        """
        if not self._computed:
            raise RuntimeError("Call compute() first")

        # Factors to remove (non-representatives in clusters)
        to_remove = set()
        for cluster in self._clusters:
            for member in cluster.members:
                if member != cluster.representative:
                    to_remove.add(member)

        return [f for f in all_factors if f not in to_remove]

    def save_correlation_matrix(self, path: str) -> None:
        """Save the full correlation matrix and analysis to JSON.

        Output includes:
            - correlation_matrix: nested dict of pairwise correlations
            - redundant_pairs: list of (f1, f2, corr) with |corr| > threshold
            - pruned_factor_list: recommended factor list after removing redundants
            - clusters: cluster assignments
        """
        if not self._computed:
            raise RuntimeError("Call compute() first")

        all_factors = list(self.correlation_matrix.keys())

        output = {
            "correlation_matrix": self.correlation_matrix,
            "redundant_pairs": [
                {"factor1": f1, "factor2": f2, "correlation": corr}
                for f1, f2, corr in self._redundant_pairs
            ],
            "pruned_factor_list": self.get_pruned_factor_list(all_factors),
            "clusters": [
                {
                    "cluster_id": c.cluster_id,
                    "members": c.members,
                    "representative": c.representative,
                }
                for c in self._clusters
            ],
            "threshold": self.threshold,
            "total_factors": len(all_factors),
            "redundant_count": len(self._redundant_pairs),
        }

        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    def _build_clusters(self, factor_names: List[str]) -> List[ClusterInfo]:
        """Build redundant factor clusters using union-find.

        Factors with abs(correlation) > threshold are merged into the same cluster.
        Each cluster picks a representative based on IC scores or alphabetical order.
        """
        # Union-Find
        parent: Dict[str, str] = {f: f for f in factor_names}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: str, b: str) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        # Union redundant pairs
        for f1, f2, corr in self._redundant_pairs:
            union(f1, f2)

        # Group by root
        groups: Dict[str, List[str]] = {}
        for f in factor_names:
            root = find(f)
            groups.setdefault(root, []).append(f)

        # Only keep clusters with >1 member
        clusters: List[ClusterInfo] = []
        cluster_id = 0
        for root, members in groups.items():
            if len(members) <= 1:
                continue
            # Pick representative: highest IC, then alphabetical
            rep = self._pick_representative(members)
            clusters.append(ClusterInfo(
                cluster_id=cluster_id,
                members=sorted(members),
                representative=rep,
            ))
            cluster_id += 1

        return clusters

    def _pick_representative(self, members: List[str]) -> str:
        """Pick the best representative from a cluster.

        Prefers the factor with highest absolute IC score.
        Falls back to first alphabetically.
        """
        if self.ic_scores:
            scored = [(f, abs(self.ic_scores.get(f, 0.0))) for f in members]
            scored.sort(key=lambda x: (-x[1], x[0]))
            return scored[0][0]
        return sorted(members)[0]


# ────────────────── Utility ──────────────────


def _pearson_correlation(x: List[float], y: List[float]) -> float:
    """Compute Pearson correlation coefficient between two lists.

    Returns 0.0 if either vector has zero variance or the lists are empty.
    """
    n = len(x)
    if n == 0 or n != len(y):
        return 0.0

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    cov = 0.0
    var_x = 0.0
    var_y = 0.0
    for i in range(n):
        dx = x[i] - mean_x
        dy = y[i] - mean_y
        cov += dx * dy
        var_x += dx * dx
        var_y += dy * dy

    if var_x == 0.0 or var_y == 0.0:
        return 0.0

    return cov / (math.sqrt(var_x) * math.sqrt(var_y))
