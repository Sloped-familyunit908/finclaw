"""
FinClaw - Portfolio Risk Dashboard
Real-time risk monitoring with VaR, concentration, sector exposure, and HTML rendering.
"""

from __future__ import annotations

import html
import math
from datetime import datetime
from typing import Any

from src.portfolio.tracker import PortfolioTracker
from src.risk.var_calculator import VaRCalculator


# Default sector mapping for common tickers
_DEFAULT_SECTORS: dict[str, str] = {
    "AAPL": "Technology", "MSFT": "Technology", "GOOGL": "Technology",
    "AMZN": "Consumer Discretionary", "TSLA": "Consumer Discretionary",
    "JPM": "Financials", "BAC": "Financials", "GS": "Financials",
    "JNJ": "Healthcare", "UNH": "Healthcare", "PFE": "Healthcare",
    "XOM": "Energy", "CVX": "Energy",
    "PG": "Consumer Staples", "KO": "Consumer Staples",
    "DIS": "Communication", "NFLX": "Communication",
}


class RiskDashboard:
    """Real-time portfolio risk monitoring dashboard."""

    def __init__(
        self,
        sector_map: dict[str, str] | None = None,
        benchmark_returns: list[float] | None = None,
    ):
        self.sector_map = sector_map or _DEFAULT_SECTORS
        self.benchmark_returns = benchmark_returns or []
        self._var_calc = VaRCalculator(confidence=0.95)
        self._var_calc_99 = VaRCalculator(confidence=0.99)

    def current_risk(self, portfolio: PortfolioTracker, prices: dict[str, float] | None = None) -> dict[str, Any]:
        """
        Compute current risk metrics for a portfolio.
        
        Returns dict with: var_95, var_99, max_position_pct, concentration_risk,
        sector_exposure, correlation_risk, beta, drawdown_current.
        """
        prices = prices or {}
        holdings = portfolio.data.holdings
        total_value = sum(
            h.quantity * prices.get(h.symbol, h.avg_cost)
            for h in holdings
        )

        if total_value <= 0:
            return self._empty_risk()

        # Position weights
        weights: dict[str, float] = {}
        for h in holdings:
            val = h.quantity * prices.get(h.symbol, h.avg_cost)
            weights[h.symbol] = val / total_value

        max_position_pct = max(weights.values()) if weights else 0.0

        # Concentration risk (Herfindahl index)
        hhi = sum(w ** 2 for w in weights.values())
        concentration_risk = hhi  # 1.0 = single stock, ~0 = well diversified

        # Sector exposure
        sector_exposure: dict[str, float] = {}
        for ticker, w in weights.items():
            sector = self.sector_map.get(ticker, "Unknown")
            sector_exposure[sector] = sector_exposure.get(sector, 0) + w

        # VaR from portfolio history
        daily_returns = self._compute_daily_returns(portfolio)
        var_95 = self._var_calc.historical(daily_returns, total_value) if len(daily_returns) >= 10 else None
        var_99 = self._var_calc_99.historical(daily_returns, total_value) if len(daily_returns) >= 10 else None

        # Current drawdown
        drawdown_current = self._current_drawdown(portfolio)

        # Beta vs benchmark
        beta = self._compute_beta(daily_returns)

        # Correlation risk (average pairwise — simplified as sector concentration)
        correlation_risk = max(sector_exposure.values()) if sector_exposure else 0.0

        return {
            "var_95": var_95.var_dollar if var_95 else 0.0,
            "var_99": var_99.var_dollar if var_99 else 0.0,
            "max_position_pct": max_position_pct,
            "concentration_risk": concentration_risk,
            "sector_exposure": sector_exposure,
            "correlation_risk": correlation_risk,
            "beta": beta,
            "drawdown_current": drawdown_current,
            "total_value": total_value,
            "num_positions": len(weights),
        }

    def render_html(self, portfolio: PortfolioTracker, prices: dict[str, float] | None = None, output_path: str = "risk_dashboard.html") -> str:
        """Render risk dashboard as HTML file. Returns the HTML string."""
        risk = self.current_risk(portfolio, prices)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        sectors_rows = ""
        for sector, weight in sorted(risk["sector_exposure"].items(), key=lambda x: -x[1]):
            bar_w = int(weight * 300)
            sectors_rows += f'<tr><td>{html.escape(sector)}</td><td>{weight:.1%}</td><td><div style="background:#4CAF50;width:{bar_w}px;height:16px;border-radius:3px"></div></td></tr>\n'

        html_content = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>FinClaw Risk Dashboard</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }}
h1 {{ color: #e94560; }} h2 {{ color: #0f3460; background: #16213e; padding: 8px 12px; border-radius: 6px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin: 20px 0; }}
.card {{ background: #16213e; border-radius: 10px; padding: 20px; text-align: center; }}
.card .value {{ font-size: 2em; font-weight: bold; color: #e94560; }}
.card .label {{ color: #999; font-size: 0.9em; margin-top: 4px; }}
table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #333; }}
th {{ background: #16213e; }}
.warn {{ color: #ff9800; }} .danger {{ color: #f44336; }} .ok {{ color: #4CAF50; }}
</style></head><body>
<h1>🦀 FinClaw Risk Dashboard</h1>
<p>Generated: {ts}</p>

<div class="grid">
<div class="card"><div class="value">${risk['total_value']:,.0f}</div><div class="label">Portfolio Value</div></div>
<div class="card"><div class="value">{risk['num_positions']}</div><div class="label">Positions</div></div>
<div class="card"><div class="value {'danger' if risk['drawdown_current'] > 0.1 else 'warn' if risk['drawdown_current'] > 0.05 else 'ok'}">{risk['drawdown_current']:.1%}</div><div class="label">Current Drawdown</div></div>
<div class="card"><div class="value">${risk['var_95']:,.0f}</div><div class="label">VaR (95%)</div></div>
<div class="card"><div class="value">${risk['var_99']:,.0f}</div><div class="label">VaR (99%)</div></div>
<div class="card"><div class="value">{risk['beta']:.2f}</div><div class="label">Beta</div></div>
<div class="card"><div class="value {'danger' if risk['max_position_pct'] > 0.25 else 'ok'}">{risk['max_position_pct']:.1%}</div><div class="label">Max Position</div></div>
<div class="card"><div class="value">{risk['concentration_risk']:.3f}</div><div class="label">HHI Concentration</div></div>
</div>

<h2>Sector Exposure</h2>
<table><tr><th>Sector</th><th>Weight</th><th>Bar</th></tr>
{sectors_rows}</table>
</body></html>"""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        return html_content

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _empty_risk(self) -> dict[str, Any]:
        return {
            "var_95": 0.0, "var_99": 0.0, "max_position_pct": 0.0,
            "concentration_risk": 0.0, "sector_exposure": {},
            "correlation_risk": 0.0, "beta": 0.0, "drawdown_current": 0.0,
            "total_value": 0.0, "num_positions": 0,
        }

    def _compute_daily_returns(self, portfolio: PortfolioTracker) -> list[float]:
        history = portfolio.data.history
        if len(history) < 2:
            return []
        values = [s.total_value if hasattr(s, 'total_value') else s.get('total_value', 0) for s in history]
        return [(values[i] / values[i-1]) - 1 for i in range(1, len(values)) if values[i-1] > 0]

    def _current_drawdown(self, portfolio: PortfolioTracker) -> float:
        history = portfolio.data.history
        if not history:
            return 0.0
        values = [s.total_value if hasattr(s, 'total_value') else s.get('total_value', 0) for s in history]
        peak = max(values)
        current = values[-1]
        return (peak - current) / peak if peak > 0 else 0.0

    def _compute_beta(self, portfolio_returns: list[float]) -> float:
        if len(portfolio_returns) < 10 or len(self.benchmark_returns) < 10:
            return 1.0  # default
        n = min(len(portfolio_returns), len(self.benchmark_returns))
        pr = portfolio_returns[-n:]
        br = self.benchmark_returns[-n:]
        mean_p = sum(pr) / n
        mean_b = sum(br) / n
        cov = sum((pr[i] - mean_p) * (br[i] - mean_b) for i in range(n)) / (n - 1)
        var_b = sum((br[i] - mean_b) ** 2 for i in range(n)) / (n - 1)
        return cov / var_b if var_b > 0 else 1.0
