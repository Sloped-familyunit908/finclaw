"""
Survivorship Bias Checker — Detect and estimate survivorship bias in backtests.

Checks whether the stock universe used in backtesting includes only
currently-listed stocks, which inflates historical returns.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np


# Known delisted tickers (US market, notable examples)
# In production, this would query a database or API
KNOWN_DELISTED = {
    # Company: (ticker, delisted_year, reason)
    'LEH': ('Lehman Brothers', 2008, 'bankruptcy'),
    'BSC': ('Bear Stearns', 2008, 'acquisition'),
    'WB': ('Wachovia', 2008, 'acquisition'),
    'ENE': ('Enron', 2001, 'bankruptcy'),
    'WCOM': ('WorldCom', 2002, 'bankruptcy'),
    'CIT': ('CIT Group', 2009, 'bankruptcy'),
    'WMI': ('Washington Mutual', 2008, 'bankruptcy'),
    'GM': ('General Motors (old)', 2009, 'bankruptcy'),
    'AIG': ('AIG (restructured)', 2009, 'restructured'),
    'FNM': ('Fannie Mae', 2010, 'delisted'),
    'FRE': ('Freddie Mac', 2010, 'delisted'),
    'SHLD': ('Sears Holdings', 2018, 'bankruptcy'),
    'LUV': ('Pier 1', 2020, 'bankruptcy'),
    'HTZ': ('Hertz (old)', 2020, 'bankruptcy'),
    'JCP': ('JCPenney', 2020, 'bankruptcy'),
    'CHK': ('Chesapeake Energy (old)', 2020, 'bankruptcy'),
    'RACE': ('Revlon', 2022, 'bankruptcy'),
    'BBBY': ('Bed Bath & Beyond', 2023, 'bankruptcy'),
    'SVB': ('Silicon Valley Bank', 2023, 'failure'),
    'FRC': ('First Republic Bank', 2023, 'failure'),
    'SIVB': ('SVB Financial', 2023, 'failure'),
}

# Typical annual survivorship bias by market
TYPICAL_BIAS = {
    'US_large_cap': 0.005,   # ~0.5% annual
    'US_small_cap': 0.015,   # ~1.5% annual
    'US_all': 0.010,         # ~1.0% annual
    'emerging': 0.020,       # ~2.0% annual
}


@dataclass
class SurvivorshipReport:
    """Survivorship bias analysis report."""
    universe_size: int
    delisted: list[dict] = field(default_factory=list)
    bias_estimate: float = 0.0  # Estimated annual return bias
    years_tested: float = 0.0
    cumulative_bias: float = 0.0  # Total bias over period
    warning: str = 'Low risk'
    recommendations: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"=== Survivorship Bias Report ===",
            f"Universe size: {self.universe_size}",
            f"Known delisted in period: {len(self.delisted)}",
            f"Estimated annual bias: {self.bias_estimate:.2%}",
            f"Period: {self.years_tested:.1f} years",
            f"Cumulative bias estimate: {self.cumulative_bias:.2%}",
            f"Risk level: {self.warning}",
        ]
        if self.delisted:
            lines.append("Delisted stocks found:")
            for d in self.delisted[:10]:
                lines.append(f"  {d['ticker']}: {d.get('name', '?')} ({d.get('reason', '?')})")
        if self.recommendations:
            lines.append("Recommendations:")
            for r in self.recommendations:
                lines.append(f"  - {r}")
        return "\n".join(lines)


class SurvivorshipBiasChecker:
    """Check for survivorship bias in a backtesting universe."""

    def __init__(self, market: str = 'US_all',
                 delisted_db: Optional[dict] = None):
        """
        Args:
            market: Market type for bias estimation
            delisted_db: Custom delisted ticker database (ticker -> info dict)
        """
        self.market = market
        self.delisted_db = delisted_db or KNOWN_DELISTED
        self.base_bias = TYPICAL_BIAS.get(market, 0.01)

    def check(self, universe: list[str], start_date: str,
              end_date: Optional[str] = None) -> dict:
        """
        Check a stock universe for survivorship bias.

        Args:
            universe: List of ticker symbols
            start_date: Backtest start date (YYYY-MM-DD)
            end_date: Backtest end date (defaults to today)

        Returns:
            Dict with delisted stocks found, bias estimate, and warning level.
        """
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d') if end_date else datetime.now()
        years = max(0.1, (end - start).days / 365.25)

        # Find known delisted stocks
        delisted = []
        universe_upper = [t.upper() for t in universe]

        for ticker, info in self.delisted_db.items():
            if isinstance(info, tuple):
                name, year, reason = info
            else:
                name = info.get('name', ticker)
                year = info.get('year', 0)
                reason = info.get('reason', 'unknown')

            # Check if this delisted stock SHOULD have been in the universe
            # (it was listed during the backtest period)
            if year and start.year <= year <= end.year:
                if ticker.upper() not in universe_upper:
                    delisted.append({
                        'ticker': ticker,
                        'name': name,
                        'year': year,
                        'reason': reason,
                    })

        # Estimate bias
        n_universe = len(universe)
        n_delisted = len(delisted)

        # Base bias adjusted for universe size and delisted count
        if n_universe > 0:
            delisted_pct = n_delisted / n_universe
            bias_estimate = self.base_bias + delisted_pct * 0.05
        else:
            bias_estimate = self.base_bias

        # Longer periods have more bias
        bias_estimate *= min(years / 5, 2.0)

        cumulative_bias = (1 + bias_estimate) ** years - 1

        # Warning level
        if bias_estimate > 0.02:
            warning = 'High survivorship bias risk'
        elif bias_estimate > 0.01:
            warning = 'Moderate survivorship bias risk'
        else:
            warning = 'Low risk'

        # Recommendations
        recs = []
        if n_delisted > 0:
            recs.append(f"Add {n_delisted} delisted stocks to universe for accurate backtesting")
        if years > 10:
            recs.append("Long backtest period — survivorship bias compounds significantly")
        if n_universe < 50:
            recs.append("Small universe is more sensitive to survivorship bias")
        if 'small_cap' in self.market.lower():
            recs.append("Small-cap universes have higher survivorship bias")
        if not recs:
            recs.append("Universe appears reasonable for the backtest period")

        report = SurvivorshipReport(
            universe_size=n_universe,
            delisted=delisted,
            bias_estimate=bias_estimate,
            years_tested=years,
            cumulative_bias=cumulative_bias,
            warning=warning,
            recommendations=recs,
        )

        return {
            'delisted': delisted,
            'bias_estimate': bias_estimate,
            'cumulative_bias': cumulative_bias,
            'warning': warning,
            'universe_size': n_universe,
            'years': years,
            'recommendations': recs,
            'report': report,
        }
