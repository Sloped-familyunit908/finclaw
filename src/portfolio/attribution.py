"""
Performance Attribution — Brinson-Fachler, factor, and risk attribution.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass
class SectorAllocation:
    """Sector-level portfolio or benchmark data."""
    sector: str
    weight: float
    ret: float  # return for the period


class PerformanceAttribution:
    """Multi-method performance attribution engine."""

    def brinson_fachler(
        self,
        portfolio: list[SectorAllocation],
        benchmark: list[SectorAllocation],
    ) -> dict:
        """Brinson-Fachler attribution decomposing active return into
        allocation, selection, and interaction effects.

        Args:
            portfolio: list of SectorAllocation for the portfolio
            benchmark: list of SectorAllocation for the benchmark

        Returns:
            dict with sector-level and total attribution effects
        """
        # Build maps
        p_map = {s.sector: s for s in portfolio}
        b_map = {s.sector: s for s in benchmark}
        sectors = sorted(set(list(p_map.keys()) + list(b_map.keys())))

        bench_total_ret = sum(s.weight * s.ret for s in benchmark)

        results = {}
        total_alloc = 0.0
        total_select = 0.0
        total_interact = 0.0

        for sec in sectors:
            wp = p_map[sec].weight if sec in p_map else 0.0
            rp = p_map[sec].ret if sec in p_map else 0.0
            wb = b_map[sec].weight if sec in b_map else 0.0
            rb = b_map[sec].ret if sec in b_map else 0.0

            allocation = (wp - wb) * (rb - bench_total_ret)
            selection = wb * (rp - rb)
            interaction = (wp - wb) * (rp - rb)

            results[sec] = {
                "allocation": round(allocation, 8),
                "selection": round(selection, 8),
                "interaction": round(interaction, 8),
                "total": round(allocation + selection + interaction, 8),
                "portfolio_weight": round(wp, 6),
                "benchmark_weight": round(wb, 6),
                "portfolio_return": round(rp, 6),
                "benchmark_return": round(rb, 6),
            }
            total_alloc += allocation
            total_select += selection
            total_interact += interaction

        port_ret = sum(s.weight * s.ret for s in portfolio)
        active_return = port_ret - bench_total_ret

        return {
            "sectors": results,
            "total_allocation": round(total_alloc, 8),
            "total_selection": round(total_select, 8),
            "total_interaction": round(total_interact, 8),
            "active_return": round(active_return, 8),
            "portfolio_return": round(port_ret, 6),
            "benchmark_return": round(bench_total_ret, 6),
        }

    def factor_attribution(
        self,
        returns: list[float],
        factors: dict[str, list[float]],
    ) -> dict:
        """Factor attribution via OLS regression.

        Args:
            returns: portfolio excess returns (T observations)
            factors: {factor_name: [factor_returns]} same length as returns

        Returns:
            dict with factor exposures (betas), R², alpha, and contribution
        """
        T = len(returns)
        if T < 2:
            return {"error": "insufficient data"}

        factor_names = sorted(factors)
        k = len(factor_names)

        # Build X matrix (with intercept)
        # Simple approach: one factor at a time for robustness
        mean_r = sum(returns) / T

        result_factors = {}
        explained_var = 0.0
        total_var = sum((r - mean_r) ** 2 for r in returns) / (T - 1)

        if total_var < 1e-12:
            return {
                "alpha": 0.0,
                "factors": {},
                "r_squared": 0.0,
                "residual_vol": 0.0,
            }

        # Multi-factor OLS: use iterative approach
        # For simplicity, compute betas via covariance method
        factor_data = {name: factors[name][:T] for name in factor_names}
        factor_means = {name: sum(factor_data[name]) / T for name in factor_names}

        # Covariance of returns with each factor
        betas = {}
        for name in factor_names:
            cov_rf = sum(
                (returns[t] - mean_r) * (factor_data[name][t] - factor_means[name])
                for t in range(T)
            ) / (T - 1)
            var_f = sum(
                (factor_data[name][t] - factor_means[name]) ** 2
                for t in range(T)
            ) / (T - 1)
            betas[name] = cov_rf / var_f if var_f > 1e-12 else 0.0

        # Alpha = mean return - sum(beta * mean factor)
        alpha = mean_r - sum(betas[name] * factor_means[name] for name in factor_names)

        # Residuals and R²
        residuals = []
        for t in range(T):
            predicted = alpha + sum(betas[name] * factor_data[name][t] for name in factor_names)
            residuals.append(returns[t] - predicted)

        ss_res = sum(r ** 2 for r in residuals)
        ss_tot = sum((r - mean_r) ** 2 for r in returns)
        r_squared = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0

        residual_vol = math.sqrt(sum(r ** 2 for r in residuals) / max(T - k - 1, 1))

        for name in factor_names:
            contribution = betas[name] * factor_means[name] * 252  # Annualized
            result_factors[name] = {
                "beta": round(betas[name], 6),
                "contribution": round(contribution, 6),
                "factor_mean": round(factor_means[name] * 252, 6),
            }

        return {
            "alpha": round(alpha * 252, 6),  # Annualized
            "factors": result_factors,
            "r_squared": round(max(r_squared, 0.0), 6),
            "residual_vol": round(residual_vol * math.sqrt(252), 6),
        }

    def risk_attribution(
        self,
        weights: dict[str, float],
        cov_matrix: dict[str, dict[str, float]],
    ) -> dict:
        """Risk attribution: decompose portfolio risk by asset.

        Args:
            weights: {ticker: weight}
            cov_matrix: {ticker_i: {ticker_j: covariance}}

        Returns:
            dict with marginal/total risk contribution per asset
        """
        tickers = sorted(weights)
        n = len(tickers)
        w = [weights[t] for t in tickers]
        cov = [[cov_matrix.get(tickers[i], {}).get(tickers[j], 0.0) for j in range(n)] for i in range(n)]

        # Portfolio variance
        port_var = sum(w[i] * w[j] * cov[i][j] for i in range(n) for j in range(n))
        port_vol = math.sqrt(max(port_var, 0.0))

        if port_vol < 1e-12:
            return {"portfolio_volatility": 0.0, "assets": {}}

        # Marginal risk contribution: MRC_i = (Cov @ w)_i / port_vol
        mrc = [sum(cov[i][j] * w[j] for j in range(n)) / port_vol for i in range(n)]
        # Component risk contribution: CRC_i = w_i * MRC_i
        crc = [w[i] * mrc[i] for i in range(n)]
        # Percentage contribution
        pct = [c / port_vol for c in crc]

        assets = {}
        for idx, t in enumerate(tickers):
            assets[t] = {
                "weight": round(w[idx], 6),
                "marginal_risk": round(mrc[idx], 6),
                "risk_contribution": round(crc[idx], 6),
                "pct_contribution": round(pct[idx], 6),
            }

        return {
            "portfolio_volatility": round(port_vol, 6),
            "assets": assets,
        }

    def generate_report(
        self,
        brinson_result: dict | None = None,
        factor_result: dict | None = None,
        risk_result: dict | None = None,
    ) -> str:
        """Generate a human-readable attribution report."""
        lines = ["=" * 60, "  PERFORMANCE ATTRIBUTION REPORT", "=" * 60, ""]

        if brinson_result:
            lines.append("── Brinson-Fachler Attribution ──")
            lines.append(f"  Portfolio Return:  {brinson_result['portfolio_return']:>8.4%}")
            lines.append(f"  Benchmark Return:  {brinson_result['benchmark_return']:>8.4%}")
            lines.append(f"  Active Return:     {brinson_result['active_return']:>8.4%}")
            lines.append("")
            lines.append(f"  {'Sector':<15} {'Alloc':>8} {'Select':>8} {'Inter':>8} {'Total':>8}")
            lines.append("  " + "-" * 47)
            for sec, data in brinson_result.get("sectors", {}).items():
                lines.append(
                    f"  {sec:<15} {data['allocation']:>8.4f} {data['selection']:>8.4f} "
                    f"{data['interaction']:>8.4f} {data['total']:>8.4f}"
                )
            lines.append("")

        if factor_result and "error" not in factor_result:
            lines.append("── Factor Attribution ──")
            lines.append(f"  Alpha (ann.):  {factor_result['alpha']:>8.4%}")
            lines.append(f"  R²:            {factor_result['r_squared']:>8.4f}")
            lines.append("")
            lines.append(f"  {'Factor':<15} {'Beta':>8} {'Contrib':>8}")
            lines.append("  " + "-" * 31)
            for name, data in factor_result.get("factors", {}).items():
                lines.append(f"  {name:<15} {data['beta']:>8.4f} {data['contribution']:>8.4f}")
            lines.append("")

        if risk_result:
            lines.append("── Risk Attribution ──")
            lines.append(f"  Portfolio Vol:  {risk_result['portfolio_volatility']:>8.4%}")
            lines.append("")
            lines.append(f"  {'Asset':<10} {'Weight':>8} {'MRC':>8} {'CRC':>8} {'%Contrib':>8}")
            lines.append("  " + "-" * 42)
            for asset, data in risk_result.get("assets", {}).items():
                lines.append(
                    f"  {asset:<10} {data['weight']:>8.4f} {data['marginal_risk']:>8.4f} "
                    f"{data['risk_contribution']:>8.4f} {data['pct_contribution']:>8.2%}"
                )
            lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)
