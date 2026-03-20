"""
FinClaw - Fama-French Factor Model
Multi-factor regression model for return attribution and prediction.

Community Edition: Standard factor model implementation.
See finclaw-pro for production parameters and calibrated factor loadings.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FactorResult:
    """Results from factor model fitting."""
    alpha: float = 0.0
    betas: dict[str, float] = field(default_factory=dict)
    r_squared: float = 0.0
    residuals: list[float] = field(default_factory=list)
    t_stats: dict[str, float] = field(default_factory=dict)
    factor_names: list[str] = field(default_factory=list)


class FactorModel:
    """
    Fama-French style multi-factor model.
    
    Fits: R_i - R_f = alpha + beta1*F1 + beta2*F2 + ... + epsilon
    
    Default factors: market, size (SMB), value (HML).
    Extensible to momentum, quality, etc.
    """

    def __init__(self, factors: list[str] | None = None):
        self.factors = factors or ["market", "size", "value"]
        self._alpha: float = 0.0
        self._betas: dict[str, float] = {}
        self._r_squared: float = 0.0
        self._residuals: list[float] = []
        self._fitted = False

    def fit(self, returns: list[float], factor_returns: dict[str, list[float]]) -> FactorResult:
        """
        Fit the factor model via OLS.
        
        returns: list of asset excess returns (R - Rf)
        factor_returns: dict mapping factor name -> list of factor returns
        
        Returns FactorResult with alpha, betas, r_squared, residuals.
        """
        n = len(returns)
        if n < 3:
            return FactorResult()

        # Validate factor data
        active_factors = []
        X_cols: list[list[float]] = []
        for f in self.factors:
            if f in factor_returns and len(factor_returns[f]) >= n:
                active_factors.append(f)
                X_cols.append(factor_returns[f][:n])

        if not active_factors:
            # No factors — just compute mean as alpha
            alpha = sum(returns) / n
            residuals = [r - alpha for r in returns]
            self._alpha = alpha
            self._betas = {}
            self._residuals = residuals
            self._fitted = True
            ss_res = sum(r**2 for r in residuals)
            mean_r = alpha
            ss_tot = sum((r - mean_r)**2 for r in returns)
            return FactorResult(alpha=alpha, betas={}, r_squared=0.0, residuals=residuals, factor_names=[])

        # OLS via normal equations: (X'X)^{-1} X'y
        # X = [1, f1, f2, ...] (with intercept)
        k = len(active_factors) + 1  # +1 for intercept

        # Build X matrix (n x k) and y vector
        y = returns[:n]

        # X'X matrix (k x k)
        XtX = [[0.0] * k for _ in range(k)]
        Xty = [0.0] * k

        for i in range(n):
            row = [1.0] + [X_cols[j][i] for j in range(len(active_factors))]
            for a in range(k):
                for b in range(k):
                    XtX[a][b] += row[a] * row[b]
                Xty[a] += row[a] * y[i]

        # Solve via Gaussian elimination
        coeffs = self._solve_linear(XtX, Xty, k)
        if coeffs is None:
            return FactorResult()

        alpha = coeffs[0]
        betas = {active_factors[j]: coeffs[j + 1] for j in range(len(active_factors))}

        # Residuals and R²
        residuals = []
        for i in range(n):
            predicted = alpha + sum(betas[f] * X_cols[j][i] for j, f in enumerate(active_factors))
            residuals.append(y[i] - predicted)

        ss_res = sum(r**2 for r in residuals)
        mean_y = sum(y) / n
        ss_tot = sum((yi - mean_y)**2 for yi in y)
        r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

        # T-statistics
        if n > k:
            mse = ss_res / (n - k)
            # Diagonal of (X'X)^{-1}
            XtX_inv = self._invert_matrix(XtX, k)
            t_stats = {}
            if XtX_inv:
                se_alpha = math.sqrt(max(mse * XtX_inv[0][0], 0))
                t_stats["alpha"] = alpha / se_alpha if se_alpha > 0 else 0
                for j, f in enumerate(active_factors):
                    se = math.sqrt(max(mse * XtX_inv[j+1][j+1], 0))
                    t_stats[f] = betas[f] / se if se > 0 else 0
            else:
                t_stats = {}
        else:
            t_stats = {}

        # Store
        self._alpha = alpha
        self._betas = betas
        self._r_squared = r_squared
        self._residuals = residuals
        self._fitted = True

        return FactorResult(
            alpha=alpha, betas=betas, r_squared=r_squared,
            residuals=residuals, t_stats=t_stats, factor_names=active_factors,
        )

    def predict(self, factor_returns: dict[str, float]) -> float:
        """Predict return given single-period factor returns."""
        if not self._fitted:
            return 0.0
        return self._alpha + sum(
            self._betas.get(f, 0) * factor_returns.get(f, 0) for f in self.factors
        )

    def decompose(self, returns: list[float], factor_returns: dict[str, list[float]]) -> dict[str, Any]:
        """
        Decompose total returns into factor contributions.
        Returns dict: { factor_name: contribution, 'alpha': ..., 'residual': ... }
        """
        if not self._fitted:
            self.fit(returns, factor_returns)

        n = len(returns)
        contributions: dict[str, float] = {"alpha": self._alpha * n}

        for f, beta in self._betas.items():
            if f in factor_returns:
                fr = factor_returns[f][:n]
                contributions[f] = beta * sum(fr) / max(len(fr), 1)
            else:
                contributions[f] = 0.0

        contributions["residual"] = sum(self._residuals) / max(len(self._residuals), 1)

        # Normalize to show percentage attribution
        total = sum(returns) / n if returns else 0
        pct: dict[str, float] = {}
        for k, v in contributions.items():
            pct[k] = v / total if total != 0 else 0

        return {
            "contributions": contributions,
            "pct_attribution": pct,
            "total_mean_return": total,
            "r_squared": self._r_squared,
        }

    # ------------------------------------------------------------------
    # Linear algebra helpers (no numpy dependency)
    # ------------------------------------------------------------------

    @staticmethod
    def _solve_linear(A: list[list[float]], b: list[float], n: int) -> list[float] | None:
        """Solve Ax = b via Gaussian elimination with partial pivoting."""
        # Augmented matrix
        M = [A[i][:] + [b[i]] for i in range(n)]

        for col in range(n):
            # Pivot
            max_row = col
            for row in range(col + 1, n):
                if abs(M[row][col]) > abs(M[max_row][col]):
                    max_row = row
            M[col], M[max_row] = M[max_row], M[col]

            if abs(M[col][col]) < 1e-12:
                return None

            # Eliminate
            for row in range(col + 1, n):
                factor = M[row][col] / M[col][col]
                for j in range(col, n + 1):
                    M[row][j] -= factor * M[col][j]

        # Back substitution
        x = [0.0] * n
        for i in range(n - 1, -1, -1):
            x[i] = (M[i][n] - sum(M[i][j] * x[j] for j in range(i + 1, n))) / M[i][i]

        return x

    @staticmethod
    def _invert_matrix(A: list[list[float]], n: int) -> list[list[float]] | None:
        """Invert matrix via Gauss-Jordan. Returns None if singular."""
        M = [A[i][:] + [1.0 if j == i else 0.0 for j in range(n)] for i in range(n)]

        for col in range(n):
            max_row = col
            for row in range(col + 1, n):
                if abs(M[row][col]) > abs(M[max_row][col]):
                    max_row = row
            M[col], M[max_row] = M[max_row], M[col]

            if abs(M[col][col]) < 1e-12:
                return None

            pivot = M[col][col]
            for j in range(2 * n):
                M[col][j] /= pivot

            for row in range(n):
                if row == col:
                    continue
                factor = M[row][col]
                for j in range(2 * n):
                    M[row][j] -= factor * M[col][j]

        return [M[i][n:] for i in range(n)]
