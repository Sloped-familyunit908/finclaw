"""Stress Testing — historical scenarios, custom shocks, and reverse stress tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Portfolio:
    """Lightweight portfolio for stress testing."""
    holdings: Dict[str, float] = field(default_factory=dict)  # ticker -> weight
    total_value: float = 100_000.0
    beta: float = 1.0
    bond_weight: float = 0.0


class StressTester:
    """Run historical and custom stress scenarios on portfolios."""

    SCENARIOS: Dict[str, dict] = {
        '2008_financial_crisis': {'market': -0.38, 'vol_spike': 3.0},
        'covid_crash': {'market': -0.34, 'recovery_months': 5},
        'dot_com_bust': {'market': -0.49, 'duration_years': 2.5},
        'rate_hike_2022': {'market': -0.19, 'bond': -0.13},
    }

    def run_scenario(self, portfolio: Portfolio, scenario: str) -> dict:
        """Apply a named historical scenario to the portfolio.

        Args:
            portfolio: Portfolio to stress.
            scenario: Key from SCENARIOS.

        Returns:
            Dict with projected_loss, stressed_value, scenario details.
        """
        if scenario not in self.SCENARIOS:
            raise ValueError(f"Unknown scenario '{scenario}'. Available: {list(self.SCENARIOS.keys())}")

        params = self.SCENARIOS[scenario]
        return self._apply_shocks(portfolio, params, scenario)

    def custom_scenario(self, portfolio: Portfolio, shocks: dict) -> dict:
        """Apply custom shock parameters.

        Args:
            portfolio: Portfolio to stress.
            shocks: Dict with keys like 'market', 'bond', 'vol_spike'.

        Returns:
            Stress test results.
        """
        return self._apply_shocks(portfolio, shocks, 'custom')

    def reverse_stress(self, portfolio: Portfolio, loss_threshold: float) -> dict:
        """Find scenarios that would cause at least the threshold loss.

        Args:
            portfolio: Portfolio to stress.
            loss_threshold: Target loss as fraction (e.g. 0.20 = 20%).

        Returns:
            Dict with triggering scenarios and required market moves.
        """
        if loss_threshold <= 0 or loss_threshold > 1:
            raise ValueError("loss_threshold must be between 0 and 1")

        triggering = []
        for name, params in self.SCENARIOS.items():
            result = self._apply_shocks(portfolio, params, name)
            if result['loss_pct'] >= loss_threshold:
                triggering.append({
                    'scenario': name,
                    'loss_pct': result['loss_pct'],
                    'stressed_value': result['stressed_value'],
                })

        # Calculate minimum market drop needed
        beta = portfolio.beta if portfolio.beta != 0 else 1.0
        required_market_drop = -loss_threshold / beta

        return {
            'loss_threshold': loss_threshold,
            'triggering_scenarios': triggering,
            'required_market_drop': round(required_market_drop, 4),
            'portfolio_beta': portfolio.beta,
        }

    def _apply_shocks(self, portfolio: Portfolio, params: dict, scenario_name: str) -> dict:
        """Core shock application logic."""
        market_shock = params.get('market', 0.0)
        bond_shock = params.get('bond', 0.0)
        vol_spike = params.get('vol_spike', 1.0)

        # Equity portion takes market shock scaled by beta
        equity_weight = 1.0 - portfolio.bond_weight
        equity_loss = market_shock * portfolio.beta * equity_weight
        bond_loss = bond_shock * portfolio.bond_weight

        total_loss_pct = equity_loss + bond_loss
        # Vol spike amplifies losses
        if vol_spike > 1.0:
            total_loss_pct *= (1 + (vol_spike - 1) * 0.1)

        stressed_value = portfolio.total_value * (1 + total_loss_pct)

        return {
            'scenario': scenario_name,
            'loss_pct': round(abs(total_loss_pct), 4),
            'loss_amount': round(portfolio.total_value - stressed_value, 2),
            'stressed_value': round(stressed_value, 2),
            'parameters': params,
        }
