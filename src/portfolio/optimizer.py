"""
Portfolio Optimizer — Markowitz mean-variance, risk-parity, Black-Litterman.

Pure-Python implementation (numpy-free) suitable for lightweight deployments.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _cov_matrix(returns: dict[str, list[float]]) -> tuple[list[str], list[list[float]]]:
    """Return (tickers, covariance_matrix) from {ticker: [daily_returns]}."""
    tickers = sorted(returns)
    n = len(tickers)
    if n == 0:
        return tickers, []
    T = min(len(returns[t]) for t in tickers)
    if T < 2:
        return tickers, [[0.0] * n for _ in range(n)]
    means = {t: _mean(returns[t][:T]) for t in tickers}
    cov = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i, n):
            ti, tj = tickers[i], tickers[j]
            val = sum(
                (returns[ti][k] - means[ti]) * (returns[tj][k] - means[tj])
                for k in range(T)
            ) / (T - 1)
            cov[i][j] = val
            cov[j][i] = val
    return tickers, cov


def _portfolio_stats(
    weights: list[float],
    mean_returns: list[float],
    cov: list[list[float]],
) -> tuple[float, float]:
    """Return (expected_return, volatility)."""
    n = len(weights)
    ret = sum(weights[i] * mean_returns[i] for i in range(n))
    var = sum(weights[i] * weights[j] * cov[i][j] for i in range(n) for j in range(n))
    return ret, math.sqrt(max(var, 0.0))


def _solve_min_var(
    cov: list[list[float]],
    target_return: float | None = None,
    mean_returns: list[float] | None = None,
    n_iter: int = 5000,
    lr: float = 0.005,
) -> list[float]:
    """Gradient-descent solver for min-variance (with optional return constraint)."""
    n = len(cov)
    w = [1.0 / n] * n

    for _ in range(n_iter):
        # gradient of w^T C w
        grad = [2 * sum(cov[i][j] * w[j] for j in range(n)) for i in range(n)]

        if target_return is not None and mean_returns is not None:
            port_ret = sum(w[i] * mean_returns[i] for i in range(n))
            lam = 50.0 * (target_return - port_ret)
            grad = [grad[i] - lam * mean_returns[i] for i in range(n)]

        # step
        w = [w[i] - lr * grad[i] for i in range(n)]
        # project to simplex (long-only, sum=1)
        w = [max(wi, 0.0) for wi in w]
        s = sum(w)
        if s > 0:
            w = [wi / s for wi in w]
        else:
            w = [1.0 / n] * n

    return w


class PortfolioOptimizer:
    """Static portfolio optimization methods."""

    @staticmethod
    def mean_variance(
        returns: dict[str, list[float]],
        target_return: float | None = None,
        risk_free: float = 0.02,
    ) -> dict:
        """Markowitz mean-variance optimization.

        Args:
            returns: {ticker: [daily_returns]}
            target_return: desired annualized return (None → max Sharpe)
            risk_free: annualized risk-free rate

        Returns:
            dict with weights, expected_return, volatility, sharpe_ratio
        """
        tickers, cov = _cov_matrix(returns)
        n = len(tickers)
        if n == 0:
            return {"weights": {}, "expected_return": 0, "volatility": 0, "sharpe_ratio": 0}

        mean_rets = [_mean(returns[t]) for t in tickers]

        if target_return is not None:
            daily_target = target_return / 252
            w = _solve_min_var(cov, daily_target, mean_rets)
        else:
            # Default to max Sharpe
            return PortfolioOptimizer.max_sharpe(returns, risk_free)

        ret, vol = _portfolio_stats(w, mean_rets, cov)
        ann_ret = ret * 252
        ann_vol = vol * math.sqrt(252)
        sharpe = (ann_ret - risk_free) / ann_vol if ann_vol > 0 else 0.0

        return {
            "weights": {tickers[i]: round(w[i], 6) for i in range(n)},
            "expected_return": round(ann_ret, 6),
            "volatility": round(ann_vol, 6),
            "sharpe_ratio": round(sharpe, 4),
        }

    @staticmethod
    def min_variance(returns: dict[str, list[float]]) -> dict:
        """Global minimum variance portfolio."""
        tickers, cov = _cov_matrix(returns)
        n = len(tickers)
        if n == 0:
            return {"weights": {}, "expected_return": 0, "volatility": 0, "sharpe_ratio": 0}

        mean_rets = [_mean(returns[t]) for t in tickers]
        w = _solve_min_var(cov)
        ret, vol = _portfolio_stats(w, mean_rets, cov)
        ann_ret = ret * 252
        ann_vol = vol * math.sqrt(252)
        sharpe = (ann_ret - 0.02) / ann_vol if ann_vol > 0 else 0.0

        return {
            "weights": {tickers[i]: round(w[i], 6) for i in range(n)},
            "expected_return": round(ann_ret, 6),
            "volatility": round(ann_vol, 6),
            "sharpe_ratio": round(sharpe, 4),
        }

    @staticmethod
    def max_sharpe(
        returns: dict[str, list[float]],
        risk_free: float = 0.02,
    ) -> dict:
        """Maximum Sharpe ratio portfolio via grid search + refinement."""
        tickers, cov = _cov_matrix(returns)
        n = len(tickers)
        if n == 0:
            return {"weights": {}, "expected_return": 0, "volatility": 0, "sharpe_ratio": 0}

        mean_rets = [_mean(returns[t]) for t in tickers]
        daily_rf = risk_free / 252

        best_sharpe = -1e18
        best_w = [1.0 / n] * n

        # Gradient ascent on Sharpe ratio
        w = [1.0 / n] * n
        for _ in range(8000):
            ret, vol = _portfolio_stats(w, mean_rets, cov)
            if vol < 1e-12:
                break
            sharpe = (ret - daily_rf) / vol

            # Gradient of Sharpe
            grad_ret = list(mean_rets)
            grad_var = [2 * sum(cov[i][j] * w[j] for j in range(n)) for i in range(n)]
            # d(Sharpe)/dw_i = (vol * mu_i - (ret-rf)/(2*vol) * grad_var_i) / vol^2
            grad = [
                (vol * grad_ret[i] - (ret - daily_rf) * grad_var[i] / (2 * vol)) / (vol * vol)
                for i in range(n)
            ]

            lr = 0.003
            w = [w[i] + lr * grad[i] for i in range(n)]
            w = [max(wi, 0.0) for wi in w]
            s = sum(w)
            if s > 0:
                w = [wi / s for wi in w]
            else:
                w = [1.0 / n] * n

            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_w = list(w)

        ret, vol = _portfolio_stats(best_w, mean_rets, cov)
        ann_ret = ret * 252
        ann_vol = vol * math.sqrt(252)
        ann_sharpe = (ann_ret - risk_free) / ann_vol if ann_vol > 0 else 0.0

        return {
            "weights": {tickers[i]: round(best_w[i], 6) for i in range(n)},
            "expected_return": round(ann_ret, 6),
            "volatility": round(ann_vol, 6),
            "sharpe_ratio": round(ann_sharpe, 4),
        }

    @staticmethod
    def risk_parity(returns: dict[str, list[float]]) -> dict:
        """Risk-parity portfolio: equal risk contribution from each asset."""
        tickers, cov = _cov_matrix(returns)
        n = len(tickers)
        if n == 0:
            return {"weights": {}, "expected_return": 0, "volatility": 0, "sharpe_ratio": 0}

        mean_rets = [_mean(returns[t]) for t in tickers]

        # Iterative: w_i proportional to 1/sigma_i, then refine
        vols = [math.sqrt(max(cov[i][i], 1e-12)) for i in range(n)]
        w = [1.0 / v for v in vols]
        s = sum(w)
        w = [wi / s for wi in w]

        # Refine with Newton-like iterations
        for _ in range(200):
            port_vol_sq = sum(w[i] * w[j] * cov[i][j] for i in range(n) for j in range(n))
            port_vol = math.sqrt(max(port_vol_sq, 1e-12))

            # Marginal risk contribution: MRC_i = (Cov @ w)_i / port_vol
            mrc = [sum(cov[i][j] * w[j] for j in range(n)) / port_vol for i in range(n)]
            # Risk contribution: RC_i = w_i * MRC_i
            rc = [w[i] * mrc[i] for i in range(n)]
            target_rc = port_vol / n

            # Adjust weights
            for i in range(n):
                if rc[i] > 0:
                    w[i] *= (target_rc / rc[i]) ** 0.3
            s = sum(w)
            if s > 0:
                w = [wi / s for wi in w]

        ret, vol = _portfolio_stats(w, mean_rets, cov)
        ann_ret = ret * 252
        ann_vol = vol * math.sqrt(252)
        sharpe = (ann_ret - 0.02) / ann_vol if ann_vol > 0 else 0.0

        return {
            "weights": {tickers[i]: round(w[i], 6) for i in range(n)},
            "expected_return": round(ann_ret, 6),
            "volatility": round(ann_vol, 6),
            "sharpe_ratio": round(sharpe, 4),
            "risk_contributions": {tickers[i]: round(w[i] * sum(cov[i][j] * w[j] for j in range(n)), 8) for i in range(n)},
        }

    @staticmethod
    def black_litterman(
        returns: dict[str, list[float]],
        market_caps: dict[str, float],
        views: list[dict],
        confidence: list[float],
        risk_aversion: float = 2.5,
        tau: float = 0.05,
    ) -> dict:
        """Black-Litterman model.

        Args:
            returns: {ticker: [daily_returns]}
            market_caps: {ticker: market_cap}
            views: list of {'assets': {ticker: weight}, 'return': expected_return}
            confidence: confidence for each view (0-1)
            risk_aversion: market risk aversion parameter
            tau: scaling factor for uncertainty

        Returns:
            dict with weights, expected_return, volatility
        """
        tickers, cov = _cov_matrix(returns)
        n = len(tickers)
        if n == 0:
            return {"weights": {}, "expected_return": 0, "volatility": 0}

        mean_rets = [_mean(returns[t]) for t in tickers]

        # Market cap weights
        total_cap = sum(market_caps.get(t, 1.0) for t in tickers)
        w_mkt = [market_caps.get(t, 1.0) / total_cap for t in tickers]

        # Implied equilibrium returns: pi = delta * Sigma * w_mkt
        pi = [risk_aversion * sum(cov[i][j] * w_mkt[j] for j in range(n)) for i in range(n)]

        # Build P (pick matrix) and Q (view returns)
        k = len(views)
        if k == 0 or k != len(confidence):
            # No views, return market-cap weights
            ret, vol = _portfolio_stats(w_mkt, mean_rets, cov)
            return {
                "weights": {tickers[i]: round(w_mkt[i], 6) for i in range(n)},
                "expected_return": round(ret * 252, 6),
                "volatility": round(vol * math.sqrt(252), 6),
            }

        P = [[0.0] * n for _ in range(k)]
        Q = [0.0] * k
        omega_diag = [0.0] * k

        for v_idx, view in enumerate(views):
            Q[v_idx] = view["return"] / 252  # Convert to daily
            for ticker, weight in view["assets"].items():
                if ticker in tickers:
                    P[v_idx][tickers.index(ticker)] = weight
            # Omega_ii = (1/confidence - 1) * P_i * tau*Sigma * P_i^T
            conf = max(min(confidence[v_idx], 0.99), 0.01)
            p_sigma_p = sum(
                P[v_idx][i] * tau * cov[i][j] * P[v_idx][j]
                for i in range(n) for j in range(n)
            )
            omega_diag[v_idx] = (1.0 / conf - 1.0) * abs(p_sigma_p)

        # BL combined return: E[R] = [(tau*Sigma)^-1 + P^T Omega^-1 P]^-1 * [(tau*Sigma)^-1 pi + P^T Omega^-1 Q]
        # Simplified: use the formula with scalar omega per view
        # Adjusted returns via each view
        bl_returns = list(pi)
        for v_idx in range(k):
            if omega_diag[v_idx] < 1e-12:
                continue
            # View residual
            p_pi = sum(P[v_idx][j] * pi[j] for j in range(n))
            residual = Q[v_idx] - p_pi
            scale = tau / (tau + omega_diag[v_idx])
            for i in range(n):
                bl_returns[i] += scale * P[v_idx][i] * residual

        # Optimal weights from BL returns: w* = (delta * Sigma)^-1 * bl_returns
        # Approximate: use gradient descent to find max-utility weights
        w = [1.0 / n] * n
        for _ in range(3000):
            grad = [
                bl_returns[i] - risk_aversion * sum(cov[i][j] * w[j] for j in range(n))
                for i in range(n)
            ]
            lr = 0.005
            w = [w[i] + lr * grad[i] for i in range(n)]
            w = [max(wi, 0.0) for wi in w]
            s = sum(w)
            if s > 0:
                w = [wi / s for wi in w]

        ret, vol = _portfolio_stats(w, mean_rets, cov)
        return {
            "weights": {tickers[i]: round(w[i], 6) for i in range(n)},
            "expected_return": round(ret * 252, 6),
            "volatility": round(vol * math.sqrt(252), 6),
            "implied_returns": {tickers[i]: round(pi[i] * 252, 6) for i in range(n)},
            "bl_returns": {tickers[i]: round(bl_returns[i] * 252, 6) for i in range(n)},
        }

    @staticmethod
    def efficient_frontier(
        returns: dict[str, list[float]],
        n_points: int = 50,
    ) -> list[dict]:
        """Compute points on the efficient frontier.

        Returns:
            List of {weights, expected_return, volatility} dicts
        """
        tickers, cov = _cov_matrix(returns)
        n = len(tickers)
        if n == 0:
            return []

        mean_rets = [_mean(returns[t]) for t in tickers]
        ann_means = [m * 252 for m in mean_rets]

        min_ret = min(ann_means)
        max_ret = max(ann_means)

        if abs(max_ret - min_ret) < 1e-10:
            result = PortfolioOptimizer.min_variance(returns)
            return [result]

        frontier = []
        for i in range(n_points):
            target = min_ret + (max_ret - min_ret) * i / (n_points - 1)
            daily_target = target / 252
            w = _solve_min_var(cov, daily_target, mean_rets, n_iter=2000)
            ret, vol = _portfolio_stats(w, mean_rets, cov)
            frontier.append({
                "weights": {tickers[j]: round(w[j], 6) for j in range(n)},
                "expected_return": round(ret * 252, 6),
                "volatility": round(vol * math.sqrt(252), 6),
            })

        return frontier
