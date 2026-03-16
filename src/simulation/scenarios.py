"""
FinClaw - Scenario Generator
Generate historical and custom market scenarios for stress testing portfolios.
"""

import math
import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Scenario:
    name: str
    description: str
    daily_returns: list[float]
    peak_drawdown: float
    duration_days: int
    recovery_days: int

    @property
    def total_return(self) -> float:
        cum = 1.0
        for r in self.daily_returns:
            cum *= (1 + r)
        return cum - 1


@dataclass
class ScenarioResult:
    scenario_name: str
    portfolio_start: float
    portfolio_end: float
    max_drawdown: float
    total_return: float
    daily_values: list[float]


# Historical crisis templates (approximate daily return parameters)
CRISIS_TEMPLATES = {
    "2008_financial_crisis": {
        "description": "2008 Global Financial Crisis — severe bear market",
        "drawdown": -0.55,
        "crash_days": 250,
        "recovery_days": 500,
        "volatility": 0.04,
    },
    "covid_2020": {
        "description": "COVID-19 crash — sharp V-shaped recovery",
        "drawdown": -0.34,
        "crash_days": 23,
        "recovery_days": 120,
        "volatility": 0.06,
    },
    "dot_com_2000": {
        "description": "Dot-com bubble burst — prolonged bear market",
        "drawdown": -0.49,
        "crash_days": 400,
        "recovery_days": 800,
        "volatility": 0.025,
    },
    "flash_crash_2010": {
        "description": "May 2010 flash crash — intraday shock",
        "drawdown": -0.09,
        "crash_days": 1,
        "recovery_days": 3,
        "volatility": 0.05,
    },
    "black_monday_1987": {
        "description": "Black Monday — single-day crash",
        "drawdown": -0.22,
        "crash_days": 1,
        "recovery_days": 60,
        "volatility": 0.08,
    },
}


class ScenarioGenerator:
    """Generate market scenarios for portfolio stress testing."""

    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)

    def generate(self, scenario_name: str, portfolio_value: float = 100000) -> ScenarioResult:
        """
        Generate returns from a named historical scenario template.

        Args:
            scenario_name: Key from CRISIS_TEMPLATES
            portfolio_value: Starting portfolio value

        Returns:
            ScenarioResult with simulated daily values
        """
        if scenario_name not in CRISIS_TEMPLATES:
            available = ", ".join(CRISIS_TEMPLATES.keys())
            raise ValueError(f"Unknown scenario '{scenario_name}'. Available: {available}")

        tmpl = CRISIS_TEMPLATES[scenario_name]
        scenario = self._build_scenario(
            name=scenario_name,
            description=tmpl["description"],
            drawdown=tmpl["drawdown"],
            crash_days=tmpl["crash_days"],
            recovery_days=tmpl["recovery_days"],
            volatility=tmpl["volatility"],
        )
        return self._apply_scenario(scenario, portfolio_value)

    def generate_custom(
        self,
        drawdown: float = -0.30,
        duration_days: int = 60,
        recovery_days: int = 120,
        volatility: float = 0.03,
        portfolio_value: float = 100000,
    ) -> ScenarioResult:
        """Generate a custom scenario with specified parameters."""
        scenario = self._build_scenario(
            name="custom",
            description=f"Custom scenario: {drawdown:.0%} drawdown over {duration_days}d",
            drawdown=drawdown,
            crash_days=duration_days,
            recovery_days=recovery_days,
            volatility=volatility,
        )
        return self._apply_scenario(scenario, portfolio_value)

    def _build_scenario(
        self, name: str, description: str,
        drawdown: float, crash_days: int, recovery_days: int, volatility: float,
    ) -> Scenario:
        """Build daily returns for a crash + recovery path."""
        daily_returns = []

        # Crash phase: drift down to drawdown target with noise
        if crash_days > 0:
            daily_drift = math.log(1 + drawdown) / crash_days
            for _ in range(crash_days):
                noise = self._rng.gauss(0, volatility)
                daily_returns.append(math.exp(daily_drift + noise) - 1)

        # Recovery phase: drift back toward 0 cumulative
        cum_after_crash = 1.0
        for r in daily_returns:
            cum_after_crash *= (1 + r)

        if recovery_days > 0 and cum_after_crash > 0:
            recovery_target = 1.0 / cum_after_crash
            daily_drift = math.log(recovery_target) / recovery_days
            for _ in range(recovery_days):
                noise = self._rng.gauss(0, volatility * 0.7)
                daily_returns.append(math.exp(daily_drift + noise) - 1)

        # Compute actual peak drawdown
        cum = 1.0
        peak = 1.0
        max_dd = 0.0
        for r in daily_returns:
            cum *= (1 + r)
            peak = max(peak, cum)
            dd = (cum - peak) / peak
            max_dd = min(max_dd, dd)

        return Scenario(
            name=name,
            description=description,
            daily_returns=daily_returns,
            peak_drawdown=max_dd,
            duration_days=crash_days,
            recovery_days=recovery_days,
        )

    def _apply_scenario(self, scenario: Scenario, portfolio_value: float) -> ScenarioResult:
        """Apply scenario returns to a portfolio value."""
        values = [portfolio_value]
        for r in scenario.daily_returns:
            values.append(values[-1] * (1 + r))

        peak = portfolio_value
        max_dd = 0.0
        for v in values:
            peak = max(peak, v)
            dd = (v - peak) / peak
            max_dd = min(max_dd, dd)

        return ScenarioResult(
            scenario_name=scenario.name,
            portfolio_start=portfolio_value,
            portfolio_end=values[-1],
            max_drawdown=max_dd,
            total_return=(values[-1] / portfolio_value) - 1,
            daily_values=values,
        )

    @staticmethod
    def list_scenarios() -> list[str]:
        """List available built-in scenario names."""
        return list(CRISIS_TEMPLATES.keys())
