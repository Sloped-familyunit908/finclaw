"""FinClaw Risk Management Module v1.2.0"""
from .position_sizing import KellyCriterion, FixedFractional, VolatilitySizing
from .stop_loss import StopLossManager, StopLossType
from .portfolio_risk import PortfolioRiskManager
from .var_calculator import VaRCalculator

__all__ = [
    "KellyCriterion", "FixedFractional", "VolatilitySizing",
    "StopLossManager", "StopLossType",
    "PortfolioRiskManager",
    "VaRCalculator",
]
