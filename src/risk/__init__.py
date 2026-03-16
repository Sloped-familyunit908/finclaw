"""FinClaw Risk Management Module v3.2.0"""
from .position_sizing import KellyCriterion, FixedFractional, VolatilitySizing
from .stop_loss import StopLossManager, StopLossType
from .portfolio_risk import PortfolioRiskManager
from .var_calculator import VaRCalculator
from .advanced_metrics import AdvancedRiskMetrics
from .stress_test import StressTester, Portfolio
from .risk_budget import RiskBudgeter

__all__ = [
    "KellyCriterion", "FixedFractional", "VolatilitySizing",
    "StopLossManager", "StopLossType",
    "PortfolioRiskManager",
    "VaRCalculator",
    "AdvancedRiskMetrics",
    "StressTester", "Portfolio",
    "RiskBudgeter",
]
