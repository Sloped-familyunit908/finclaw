"""
Factor Quality Analysis — IC, IR, decay, and tiering for all registered factors.

Computes Rank IC (Spearman), IC consistency, Information Ratio, hit rate,
and IC decay curves across multiple forward-return horizons.  Assigns each
factor a quality tier (A/B/C/D) and produces a JSON report with pruning
recommendations.
"""

import json
import math
from typing import Any, Dict, List, Optional, Tuple

from .factor_analysis import compute_ic, compute_ir, _rank
from .factor_discovery import FactorRegistry


# ── Quality-tier thresholds ──────────────────────────────────
TIER_A_IC = 0.05
TIER_A_IR = 0.5
TIER_B_IC = 0.03
TIER_B_IR = 0.3
TIER_C_IC = 0.01

DECAY_PERIODS: List[int] = [1, 3, 5, 10, 20]
MAX_STOCKS = 100


def _forward_returns(
    closes: List[float], idx: int, period: int
) -> Optional[float]:
    """Compute forward N-day return at *idx*.

    Returns ``None`` when *idx + period* is beyond the close series.
    """
    if idx + period >= len(closes) or idx < 0:
        return None
    c0 = closes[idx]
    if c0 == 0:
        return None
    return (closes[idx + period] - c0) / c0


def _classify_tier(abs_ic_mean: float, ir: float) -> str:
    """Assign a quality tier from IC mean and IR."""
    if abs_ic_mean > TIER_A_IC and ir > TIER_A_IR:
        return "A"
    if abs_ic_mean > TIER_B_IC and ir > TIER_B_IR:
        return "B"
    if abs_ic_mean > TIER_C_IC:
        return "C"
    return "D"


class FactorQualityAnalyzer:
    """Evaluate every factor in a :class:`FactorRegistry` against stock data.

    Parameters
    ----------
    stock_data : dict
        ``{code: {"date": [...], "open": [...], "high": [...],
        "low": [...], "close": [...], "volume": [...]}}``
    registry : FactorRegistry
        Must already have factors loaded (``registry.load_all()``).
    max_stocks : int
        Sample at most this many stocks for speed.
    """

    def __init__(
        self,
        stock_data: Dict[str, Dict[str, list]],
        registry: FactorRegistry,
        max_stocks: int = MAX_STOCKS,
    ):
        self.stock_data = stock_data
        self.registry = registry
        self.max_stocks = max_stocks
        # Cache of analysis results keyed by factor name
        self._results: Dict[str, Dict[str, Any]] = {}

    # ── public API ───────────────────────────────────────────

    def analyze_all(
        self, periods: Optional[List[int]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Run IC / IR / decay / tier analysis for every registered factor.

        Returns a dict keyed by factor name with sub-keys:
        ``ic_mean``, ``ic_std``, ``ir``, ``hit_rate``,
        ``decay`` (dict period→IC), ``tier``.
        """
        if periods is None:
            periods = list(DECAY_PERIODS)

        codes = list(self.stock_data.keys())[: self.max_stocks]
        factor_names = self.registry.list_factors()

        for fname in factor_names:
            self._results[fname] = self._analyze_factor(fname, codes, periods)
        return self._results

    def get_tier(self, factor_name: str) -> str:
        """Return the quality tier for *factor_name* (must call analyze_all first)."""
        entry = self._results.get(factor_name)
        if entry is None:
            return "D"
        return entry["tier"]

    def get_results(self) -> Dict[str, Dict[str, Any]]:
        """Return cached analysis results."""
        return dict(self._results)

    def generate_factor_report(self) -> Dict[str, Any]:
        """Build a JSON-serialisable report.

        Includes all factors ranked by |IC|, decay curves, tier
        assignments, and pruning recommendations.
        """
        if not self._results:
            self.analyze_all()

        ranked = sorted(
            self._results.items(),
            key=lambda kv: abs(kv[1]["ic_mean"]),
            reverse=True,
        )

        factors_list: List[Dict[str, Any]] = []
        keep: List[str] = []
        drop: List[str] = []

        for name, info in ranked:
            entry = {
                "name": name,
                "ic_mean": info["ic_mean"],
                "ic_std": info["ic_std"],
                "ir": info["ir"],
                "hit_rate": info["hit_rate"],
                "tier": info["tier"],
                "decay": {str(k): v for k, v in info["decay"].items()},
            }
            factors_list.append(entry)
            if info["tier"] in ("A", "B"):
                keep.append(name)
            elif info["tier"] == "D":
                drop.append(name)

        tier_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
        for info in self._results.values():
            tier_counts[info["tier"]] += 1

        report: Dict[str, Any] = {
            "total_factors": len(self._results),
            "tier_summary": tier_counts,
            "factors": factors_list,
            "recommendations": {
                "keep": keep,
                "drop": drop,
                "keep_count": len(keep),
                "drop_count": len(drop),
            },
        }
        return report

    # ── internals ────────────────────────────────────────────

    def _analyze_factor(
        self,
        factor_name: str,
        codes: List[str],
        periods: List[int],
    ) -> Dict[str, Any]:
        """Compute IC series and derived metrics for one factor."""
        factor_meta = self.registry.factors.get(factor_name)
        if factor_meta is None:
            return self._empty_result(periods)

        compute_fn = factor_meta.compute_fn

        # For the IC-mean / IR / hit-rate we use the *first* period
        # (defaults to 1d).  Decay uses all periods.
        base_period = periods[0] if periods else 1

        # Gather per-date IC values and per-period IC values for decay
        ic_series: List[float] = []  # daily IC for base_period
        decay_ic_accum: Dict[int, List[float]] = {p: [] for p in periods}

        # Build a common date-length from the stock data.  We iterate
        # over evaluation dates and compute cross-sectional IC.
        # Choose the shortest stock series to determine valid date range.
        min_len = self._min_series_length(codes)
        if min_len < 30:
            return self._empty_result(periods)

        max_period = max(periods) if periods else 20
        # Evaluation window: from day 30 to (min_len - max_period - 1)
        start_idx = 30
        end_idx = min_len - max_period - 1
        if end_idx <= start_idx:
            return self._empty_result(periods)

        for idx in range(start_idx, end_idx + 1):
            scores: List[float] = []
            fwd_by_period: Dict[int, List[float]] = {p: [] for p in periods}
            for code in codes:
                sd = self.stock_data[code]
                closes = sd["close"]
                highs = sd["high"]
                lows = sd["low"]
                volumes = sd["volume"]
                try:
                    val = compute_fn(closes, highs, lows, volumes, idx)
                    val = max(0.0, min(1.0, float(val)))
                except Exception:
                    val = 0.5
                scores.append(val)
                for p in periods:
                    ret = _forward_returns(closes, idx, p)
                    if ret is None:
                        ret = 0.0
                    fwd_by_period[p].append(ret)

            if len(scores) < 10:
                continue

            # Cross-sectional IC for base period
            ic_val = compute_ic(scores, fwd_by_period[base_period])
            ic_series.append(ic_val)

            # Decay ICs
            for p in periods:
                decay_ic_accum[p].append(
                    compute_ic(scores, fwd_by_period[p])
                )

        # Aggregate
        if not ic_series:
            return self._empty_result(periods)

        ic_mean = float(_safe_mean(ic_series))
        ic_std = float(_safe_std(ic_series))
        ir = float(compute_ir(ic_series))
        hit_rate = sum(1 for x in ic_series if x > 0) / len(ic_series)
        hit_rate = round(hit_rate, 4)

        decay: Dict[int, float] = {}
        for p in periods:
            vals = decay_ic_accum[p]
            decay[p] = round(float(_safe_mean(vals)), 4) if vals else 0.0

        tier = _classify_tier(abs(ic_mean), ir)

        return {
            "ic_mean": round(ic_mean, 4),
            "ic_std": round(ic_std, 4),
            "ir": ir,
            "hit_rate": hit_rate,
            "decay": decay,
            "tier": tier,
        }

    def _min_series_length(self, codes: List[str]) -> int:
        """Return the shortest close-price series length across *codes*."""
        if not codes:
            return 0
        lengths = []
        for c in codes:
            sd = self.stock_data.get(c)
            if sd is None:
                continue
            lengths.append(len(sd.get("close", [])))
        return min(lengths) if lengths else 0

    @staticmethod
    def _empty_result(periods: List[int]) -> Dict[str, Any]:
        return {
            "ic_mean": 0.0,
            "ic_std": 0.0,
            "ir": 0.0,
            "hit_rate": 0.0,
            "decay": {p: 0.0 for p in periods},
            "tier": "D",
        }


# ── helpers ──────────────────────────────────────────────────

def _safe_mean(vals: List[float]) -> float:
    if not vals:
        return 0.0
    return sum(vals) / len(vals)


def _safe_std(vals: List[float]) -> float:
    if len(vals) < 2:
        return 0.0
    m = _safe_mean(vals)
    var = sum((v - m) ** 2 for v in vals) / len(vals)
    return math.sqrt(var)
