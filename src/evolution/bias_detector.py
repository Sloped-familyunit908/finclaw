"""
Backtest Bias Detector — detect lookahead bias, data snooping, and survivorship bias.

Inspired by Freqtrade's lookahead-analysis and recursive-analysis.
Ensures backtest results are trustworthy by catching common pitfalls.

Three detection modes:
  1. Look-ahead Bias: factor uses future data beyond idx
  2. Data Snooping: strategy overfits training data (train >> test performance)
  3. Survivorship Bias: missing tail data suggests delisted stocks
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np


# ============================================================
# Data Structures
# ============================================================


@dataclass
class BiasReport:
    """Report for a single factor's lookahead bias check."""

    factor_name: str
    has_lookahead: bool
    details: str
    severity: str  # "CLEAN" / "WARNING" / "CRITICAL"

    def __post_init__(self):
        if self.severity not in ("CLEAN", "WARNING", "CRITICAL"):
            raise ValueError(f"Invalid severity: {self.severity!r}")


@dataclass
class SnoopingReport:
    """Report for data snooping / overfitting detection."""

    dna_id: str
    train_return: float
    test_return: float
    overfit_ratio: float  # train_return / test_return (or inf)
    risk_level: str  # "LOW" / "MEDIUM" / "HIGH" / "EXTREME"
    details: str

    def __post_init__(self):
        if self.risk_level not in ("LOW", "MEDIUM", "HIGH", "EXTREME"):
            raise ValueError(f"Invalid risk_level: {self.risk_level!r}")


# ============================================================
# Look-ahead Bias Detection
# ============================================================


def detect_lookahead(
    factor_fn: Callable,
    test_data: Dict[str, list],
    sample_indices: Optional[List[int]] = None,
    tolerance: float = 1e-9,
) -> BiasReport:
    """Detect look-ahead bias in a single factor function.

    Method: call the factor twice for each sample index —
      1. With full data (factor can potentially peek ahead)
      2. With data truncated right after idx (no future available)
    If results differ, the factor is using future data.

    Parameters
    ----------
    factor_fn : callable
        Signature: (closes, highs, lows, volumes, idx) -> float
    test_data : dict
        Keys: "closes", "highs", "lows", "volumes" — each a list of floats.
    sample_indices : list[int], optional
        Which indices to test. Defaults to ~10 evenly spaced points.
    tolerance : float
        Maximum allowed difference before flagging lookahead.

    Returns
    -------
    BiasReport
    """
    closes = test_data["closes"]
    highs = test_data["highs"]
    lows = test_data["lows"]
    volumes = test_data["volumes"]
    n = len(closes)

    if n < 10:
        return BiasReport(
            factor_name=getattr(factor_fn, "__name__", str(factor_fn)),
            has_lookahead=False,
            details="Insufficient data for lookahead test (need >= 10 bars).",
            severity="WARNING",
        )

    # Pick sample indices
    if sample_indices is None:
        step = max(1, (n - 20) // 10)
        sample_indices = list(range(10, n - 5, step))
        if not sample_indices:
            sample_indices = [n // 2]

    mismatches: List[Tuple[int, float, float]] = []

    for idx in sample_indices:
        if idx < 0 or idx >= n:
            continue

        # Full data result
        try:
            full_result = factor_fn(closes, highs, lows, volumes, idx)
        except Exception:
            full_result = float("nan")

        # Truncated data result — cut off everything after idx
        trunc_closes = closes[: idx + 1]
        trunc_highs = highs[: idx + 1]
        trunc_lows = lows[: idx + 1]
        trunc_volumes = volumes[: idx + 1]

        try:
            trunc_result = factor_fn(
                trunc_closes, trunc_highs, trunc_lows, trunc_volumes, idx
            )
        except Exception:
            trunc_result = float("nan")

        # Compare
        if math.isnan(full_result) and math.isnan(trunc_result):
            continue  # both NaN, consider same
        if math.isnan(full_result) != math.isnan(trunc_result):
            mismatches.append((idx, full_result, trunc_result))
            continue

        if abs(full_result - trunc_result) > tolerance:
            mismatches.append((idx, full_result, trunc_result))

    factor_name = getattr(factor_fn, "__name__", str(factor_fn))

    if not mismatches:
        return BiasReport(
            factor_name=factor_name,
            has_lookahead=False,
            details=f"Tested {len(sample_indices)} indices. No lookahead detected.",
            severity="CLEAN",
        )

    # Determine severity based on mismatch rate
    mismatch_rate = len(mismatches) / len(sample_indices)
    if mismatch_rate > 0.5:
        severity = "CRITICAL"
    else:
        severity = "WARNING"

    detail_lines = [
        f"Lookahead detected at {len(mismatches)}/{len(sample_indices)} indices "
        f"({mismatch_rate:.0%})."
    ]
    for idx, full_val, trunc_val in mismatches[:5]:  # show first 5
        detail_lines.append(f"  idx={idx}: full={full_val:.6f}, truncated={trunc_val:.6f}")
    if len(mismatches) > 5:
        detail_lines.append(f"  ... and {len(mismatches) - 5} more")

    return BiasReport(
        factor_name=factor_name,
        has_lookahead=True,
        details="\n".join(detail_lines),
        severity=severity,
    )


def detect_lookahead_batch(
    factors: Dict[str, Callable],
    test_data: Dict[str, list],
    tolerance: float = 1e-9,
) -> List[BiasReport]:
    """Run lookahead detection on all factors in a dict.

    Parameters
    ----------
    factors : dict[str, callable]
        Factor name -> compute function.
    test_data : dict
        OHLCV data with keys: closes, highs, lows, volumes.

    Returns
    -------
    list[BiasReport]
    """
    reports = []
    for name, fn in factors.items():
        report = detect_lookahead(fn, test_data, tolerance=tolerance)
        report.factor_name = name  # ensure name matches registry
        reports.append(report)
    return reports


# ============================================================
# Data Snooping Detection
# ============================================================


def _simple_backtest_return(
    dna_weights: Dict[str, float],
    factor_fns: Dict[str, Callable],
    data: Dict[str, list],
    start_idx: int = 20,
) -> float:
    """Run a ultra-simple backtest: weighted factor signal → daily P&L.

    Simulates a long/short strategy based on combined factor score.
    Score > 0.6 → long, score < 0.4 → short, else flat.

    Returns total cumulative return as a fraction (e.g. 0.15 = 15%).
    """
    closes = data["closes"]
    highs = data["highs"]
    lows = data["lows"]
    volumes = data["volumes"]
    n = len(closes)

    if n < start_idx + 5:
        return 0.0

    cumulative = 0.0
    total_weight = sum(abs(w) for w in dna_weights.values()) or 1.0

    for idx in range(start_idx, n - 1):
        # Compute weighted factor score
        score = 0.0
        for fname, weight in dna_weights.items():
            if fname in factor_fns:
                try:
                    val = factor_fns[fname](closes, highs, lows, volumes, idx)
                    val = max(0.0, min(1.0, float(val)))
                except Exception:
                    val = 0.5
                score += weight * val

        score /= total_weight  # normalize to [0, 1]

        # Tomorrow's return
        if closes[idx] > 0:
            daily_ret = (closes[idx + 1] - closes[idx]) / closes[idx]
        else:
            daily_ret = 0.0

        # Position
        if score > 0.6:
            cumulative += daily_ret  # long
        elif score < 0.4:
            cumulative -= daily_ret  # short

    return cumulative


def detect_snooping(
    dna: Dict,
    train_data: Dict[str, list],
    test_data: Dict[str, list],
    factor_fns: Optional[Dict[str, Callable]] = None,
) -> SnoopingReport:
    """Detect data snooping / overfitting by comparing train vs test performance.

    Parameters
    ----------
    dna : dict
        Must have "id" (str) and "weights" (dict[str, float]).
    train_data, test_data : dict
        OHLCV data dicts with keys: closes, highs, lows, volumes.
    factor_fns : dict, optional
        Factor name -> compute function. If None, uses trivial factors.

    Returns
    -------
    SnoopingReport
    """
    dna_id = dna.get("id", "unknown")
    weights = dna.get("weights", {})

    if factor_fns is None:
        # Fallback: create trivial factors based on weight keys
        factor_fns = {}
        for name in weights:
            # Just return 0.5 — this detects purely structural snooping
            factor_fns[name] = lambda c, h, l, v, i: 0.5

    train_ret = _simple_backtest_return(weights, factor_fns, train_data)
    test_ret = _simple_backtest_return(weights, factor_fns, test_data)

    # Compute overfit ratio
    if abs(test_ret) < 1e-10:
        if abs(train_ret) < 1e-10:
            overfit_ratio = 1.0
        else:
            overfit_ratio = float("inf")
    else:
        overfit_ratio = abs(train_ret / test_ret)

    # Classify risk
    # Also check sign flip: positive train but negative test
    sign_flip = (train_ret > 0.01 and test_ret < -0.01)

    if sign_flip:
        risk_level = "EXTREME"
    elif overfit_ratio > 5.0 or overfit_ratio == float("inf"):
        risk_level = "EXTREME"
    elif overfit_ratio > 3.0:
        risk_level = "HIGH"
    elif overfit_ratio > 2.0:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    details_parts = [
        f"Train return: {train_ret:+.2%}",
        f"Test return: {test_ret:+.2%}",
        f"Overfit ratio: {overfit_ratio:.2f}x",
    ]
    if sign_flip:
        details_parts.append("⚠ Sign flip detected: profitable on train, losing on test!")

    return SnoopingReport(
        dna_id=dna_id,
        train_return=train_ret,
        test_return=test_ret,
        overfit_ratio=overfit_ratio,
        risk_level=risk_level,
        details=" | ".join(details_parts),
    )


# ============================================================
# Survivorship Bias Warning
# ============================================================


def check_survivorship(
    stock_data: Dict[str, Dict[str, list]],
    data_start_date: Optional[str] = None,
    tail_missing_threshold: float = 0.1,
) -> List[str]:
    """Check for potential survivorship bias in stock data.

    Heuristic: if a stock's data ends significantly before the latest date
    in the dataset (large tail gap), it may have been delisted.

    Parameters
    ----------
    stock_data : dict[str, dict]
        Mapping of stock_code -> OHLCV data dict.
        Each dict must have "closes" (list of floats).
        NaN or 0.0 at the tail indicates missing data.
    data_start_date : str, optional
        For informational purposes only.
    tail_missing_threshold : float
        Fraction of data that must be missing at the tail to flag.
        Default 0.1 (10%).

    Returns
    -------
    list[str]
        Warning messages for stocks with potential survivorship bias.
    """
    warnings: List[str] = []

    if not stock_data:
        return warnings

    # Find the maximum data length across all stocks
    max_len = max(len(d.get("closes", [])) for d in stock_data.values())

    if max_len == 0:
        return warnings

    for code, data in stock_data.items():
        closes = data.get("closes", [])
        n = len(closes)

        if n == 0:
            warnings.append(f"{code}: No data at all — possibly delisted or invalid code.")
            continue

        # Check if data is shorter than the longest series
        if n < max_len:
            missing_frac = (max_len - n) / max_len
            if missing_frac >= tail_missing_threshold:
                warnings.append(
                    f"{code}: Data length {n} vs max {max_len} "
                    f"({missing_frac:.0%} shorter) — possible delisting."
                )
                continue

        # Check for NaN/zero tail
        tail_missing = 0
        for i in range(n - 1, -1, -1):
            val = closes[i]
            if val == 0.0 or (isinstance(val, float) and math.isnan(val)):
                tail_missing += 1
            else:
                break

        if tail_missing > 0:
            missing_frac = tail_missing / n
            if missing_frac >= tail_missing_threshold:
                warnings.append(
                    f"{code}: Last {tail_missing}/{n} bars are zero/NaN "
                    f"({missing_frac:.0%}) — likely delisted."
                )

    return warnings


# ============================================================
# Convenience: generate test data
# ============================================================


def make_test_ohlcv(n: int = 200, seed: int = 42) -> Dict[str, list]:
    """Generate synthetic OHLCV data for testing.

    Returns dict with keys: closes, highs, lows, volumes.
    """
    rng = np.random.RandomState(seed)
    returns = rng.normal(0.001, 0.02, n)
    closes = [100.0]
    for r in returns[1:]:
        closes.append(closes[-1] * (1 + r))

    highs = [c * (1 + abs(rng.normal(0, 0.01))) for c in closes]
    lows = [c * (1 - abs(rng.normal(0, 0.01))) for c in closes]
    volumes = [int(1e6 * (1 + rng.uniform(-0.5, 0.5))) for _ in closes]

    return {
        "closes": closes,
        "highs": highs,
        "lows": lows,
        "volumes": volumes,
    }
