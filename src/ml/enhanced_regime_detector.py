"""
Enhanced Market Regime Detector
===============================

Regime detection inspired by autoencoder reconstruction-error approach
from "Adaptive Regime-Aware Stock Price Prediction" (arXiv:2603.19136).

Uses statistical anomaly detection as a lightweight, pure-NumPy alternative
to neural autoencoders.  Detects market regimes by measuring deviation from
historical "normal" market conditions via:

  1. Volatility clustering — rolling volatility vs. historical baseline
  2. Mean-shift detection  — z-score of rolling returns vs. expanding mean
  3. Reconstruction error  — Mahalanobis-like distance of current feature
     vector from the historical "normal" distribution

Three regimes:
  • stable   — low volatility, returns close to long-run mean
  • volatile — elevated volatility but no extreme drawdown
  • crash    — extreme downside moves or very high reconstruction error
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence


@dataclass
class RegimeResult:
    """Result of a single regime detection call."""

    regime: str          # 'stable', 'volatile', or 'crash'
    score: float         # 0.0 (perfectly stable) … 1.0 (extreme anomaly)
    volatility: float    # annualised rolling volatility
    mean_return: float   # rolling mean return
    vol_z: float         # z-score of rolling vol vs. baseline
    ret_z: float         # z-score of rolling return vs. baseline
    reconstruction_error: float  # composite anomaly distance


class EnhancedRegimeDetector:
    """Regime detection inspired by autoencoder approach (arXiv:2603.19136).

    Uses statistical anomaly detection as a lightweight alternative to
    neural autoencoders.  Detects market regimes by measuring deviation
    from historical 'normal' market conditions.
    """

    # ── thresholds ───────────────────────────────────────────────
    VOLATILE_SCORE = 0.35   # score above this → volatile
    CRASH_SCORE    = 0.70   # score above this → crash

    def __init__(
        self,
        lookback: int = 20,
        baseline_window: int = 252,
        annualise_factor: float = 252.0,
        volatile_threshold: float | None = None,
        crash_threshold: float | None = None,
    ):
        """
        Parameters
        ----------
        lookback : int
            Rolling window for current regime features (default 20 ≈ 1 month).
        baseline_window : int
            Expanding / rolling window that defines "normal" (default 252 ≈ 1 year).
        annualise_factor : float
            Trading days per year, used to annualise volatility.
        volatile_threshold, crash_threshold : float | None
            Override class-level VOLATILE_SCORE / CRASH_SCORE.
        """
        if lookback < 2:
            raise ValueError("lookback must be >= 2")
        if baseline_window < lookback:
            raise ValueError("baseline_window must be >= lookback")

        self.lookback = lookback
        self.baseline_window = baseline_window
        self.annualise_factor = annualise_factor
        self.volatile_threshold = volatile_threshold if volatile_threshold is not None else self.VOLATILE_SCORE
        self.crash_threshold = crash_threshold if crash_threshold is not None else self.CRASH_SCORE

    # ── public API ───────────────────────────────────────────────

    def detect_regime(
        self,
        prices: Sequence[float],
        volumes: Sequence[float] | None = None,
    ) -> str:
        """Return current market regime: ``'stable'``, ``'volatile'``, or ``'crash'``."""
        result = self._compute(prices, volumes)
        return result.regime

    def regime_score(
        self,
        prices: Sequence[float],
        volumes: Sequence[float] | None = None,
    ) -> float:
        """Return anomaly score in [0.0, 1.0].

        0.0 = perfectly stable,  1.0 = extreme anomaly / crash.
        """
        result = self._compute(prices, volumes)
        return result.score

    def detect_detailed(
        self,
        prices: Sequence[float],
        volumes: Sequence[float] | None = None,
    ) -> RegimeResult:
        """Full diagnostic result including z-scores and reconstruction error."""
        return self._compute(prices, volumes)

    def adaptive_weights(self, regime: str) -> dict[str, float]:
        """Return scoring weights adapted to the current regime.

        Stable   → more weight on momentum/trend signals
        Volatile → more weight on mean-reversion / RSI signals
        Crash    → more weight on risk / drawdown protection
        """
        regime = regime.lower()
        if regime == "stable":
            return {
                "momentum": 0.35,
                "trend": 0.30,
                "mean_reversion": 0.10,
                "rsi": 0.10,
                "risk": 0.05,
                "drawdown": 0.05,
                "volume": 0.05,
            }
        elif regime == "volatile":
            return {
                "momentum": 0.10,
                "trend": 0.10,
                "mean_reversion": 0.25,
                "rsi": 0.25,
                "risk": 0.15,
                "drawdown": 0.10,
                "volume": 0.05,
            }
        elif regime == "crash":
            return {
                "momentum": 0.05,
                "trend": 0.05,
                "mean_reversion": 0.10,
                "rsi": 0.10,
                "risk": 0.30,
                "drawdown": 0.30,
                "volume": 0.10,
            }
        else:
            raise ValueError(f"Unknown regime: {regime!r}; expected 'stable', 'volatile', or 'crash'")

    # ── internals ────────────────────────────────────────────────

    def _returns(self, prices: Sequence[float]) -> list[float]:
        """Simple returns from a price series."""
        return [(prices[i] / prices[i - 1]) - 1.0 for i in range(1, len(prices))]

    @staticmethod
    def _mean(xs: Sequence[float]) -> float:
        if not xs:
            return 0.0
        return sum(xs) / len(xs)

    @staticmethod
    def _std(xs: Sequence[float], mean: float | None = None) -> float:
        n = len(xs)
        if n < 2:
            return 0.0
        if mean is None:
            mean = sum(xs) / n
        var = sum((x - mean) ** 2 for x in xs) / (n - 1)
        return math.sqrt(var) if var > 0 else 0.0

    def _compute(
        self,
        prices: Sequence[float],
        volumes: Sequence[float] | None = None,
    ) -> RegimeResult:
        prices = list(prices)
        n = len(prices)

        # Minimum data guard
        min_required = self.lookback + 1  # need lookback returns
        if n < min_required:
            return RegimeResult(
                regime="stable",
                score=0.0,
                volatility=0.0,
                mean_return=0.0,
                vol_z=0.0,
                ret_z=0.0,
                reconstruction_error=0.0,
            )

        rets = self._returns(prices)

        # ── 1. Rolling features (current regime) ─────────────
        window = rets[-self.lookback:]
        roll_mean = self._mean(window)
        roll_std = self._std(window, roll_mean)
        roll_vol = roll_std * math.sqrt(self.annualise_factor)

        # ── 2. Baseline statistics ("normal") ────────────────
        baseline_rets = rets[-self.baseline_window:] if len(rets) > self.baseline_window else rets
        base_mean = self._mean(baseline_rets)
        base_std = self._std(baseline_rets, base_mean)

        # Guard: if baseline has no variation, treat as stable
        if base_std == 0.0:
            return RegimeResult(
                regime="stable",
                score=0.0,
                volatility=roll_vol,
                mean_return=roll_mean,
                vol_z=0.0,
                ret_z=0.0,
                reconstruction_error=0.0,
            )

        # z-score of rolling vol vs baseline vol
        # compute baseline rolling vol for comparison
        baseline_vols: list[float] = []
        for i in range(self.lookback, len(baseline_rets) + 1):
            w = baseline_rets[i - self.lookback : i]
            baseline_vols.append(self._std(w))

        if len(baseline_vols) >= 2:
            bvol_mean = self._mean(baseline_vols)
            bvol_std = self._std(baseline_vols, bvol_mean)
            vol_z = (roll_std - bvol_mean) / bvol_std if bvol_std > 0 else 0.0
        else:
            vol_z = 0.0

        # z-score of rolling return vs baseline return
        ret_z = (roll_mean - base_mean) / base_std

        # ── 3. Volume anomaly (optional) ─────────────────────
        vol_anomaly = 0.0
        if volumes is not None and len(volumes) >= self.lookback + 1:
            vol_list = list(volumes)
            recent_vol = vol_list[-self.lookback:]
            baseline_vol = vol_list[-(self.baseline_window):] if len(vol_list) > self.baseline_window else vol_list
            if len(baseline_vol) >= 2:
                bv_mean = self._mean(baseline_vol)
                bv_std = self._std(baseline_vol, bv_mean)
                if bv_std > 0:
                    cur_v_mean = self._mean(recent_vol)
                    vol_anomaly = abs((cur_v_mean - bv_mean) / bv_std)

        # ── 4. Reconstruction error ──────────────────────────
        # Composite anomaly distance: weighted sum of squared z-scores
        recon_error = math.sqrt(
            0.50 * max(vol_z, 0) ** 2   # upside vol is bad
            + 0.30 * ret_z ** 2
            + 0.20 * vol_anomaly ** 2
        )

        # ── 5. Score → [0, 1] via sigmoid-like mapping ──────
        # We use 1 - exp(-k * recon_error) so 0 maps to 0 and ∞ maps to 1.
        k = 0.6  # scale factor
        score = 1.0 - math.exp(-k * recon_error)
        score = max(0.0, min(1.0, score))

        # ── 6. Crash override: large drawdown in the window ─
        # If the window has a drawdown > 10%, boost score toward crash.
        peak = prices[-self.lookback - 1]
        max_dd = 0.0
        for p in prices[-self.lookback:]:
            if p > peak:
                peak = p
            dd = (p - peak) / peak if peak != 0 else 0.0
            if dd < max_dd:
                max_dd = dd
        if max_dd < -0.10:
            # Scale: -10% → +0.15, -20% → +0.30, -30% → +0.45
            crash_boost = abs(max_dd) * 1.5
            score = min(1.0, score + crash_boost)

        # ── 7. Classify ─────────────────────────────────────
        if score >= self.crash_threshold:
            regime = "crash"
        elif score >= self.volatile_threshold:
            regime = "volatile"
        else:
            regime = "stable"

        return RegimeResult(
            regime=regime,
            score=round(score, 4),
            volatility=round(roll_vol, 6),
            mean_return=round(roll_mean, 6),
            vol_z=round(vol_z, 4),
            ret_z=round(ret_z, 4),
            reconstruction_error=round(recon_error, 4),
        )
