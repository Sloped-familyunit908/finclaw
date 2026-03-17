"""
FinClaw Built-in Strategy Library v5.0.0
========================================
Production-ready strategies for crypto, stocks, and universal markets.
"""

from .base import Strategy, StrategySignal, StrategyMeta
from .grid_trading import GridTradingStrategy
from .funding_rate import FundingRateArbitrage
from .dca import DCAStrategy
from .pairs_trading import PairsTradingStrategy
from .sector_rotation import SectorRotationStrategy
from .dividend_harvest import DividendHarvestStrategy
from .trend_following import TrendFollowingStrategy
from .breakout import BreakoutStrategy
from .mean_reversion_bb import MeanReversionBBStrategy
from .multi_factor import MultiFactorStrategy
from .btc_cycle import BTCCycleIndicator

STRATEGY_REGISTRY: dict[str, type["Strategy"]] = {
    "grid-trading": GridTradingStrategy,
    "funding-rate": FundingRateArbitrage,
    "dca": DCAStrategy,
    "pairs-trading": PairsTradingStrategy,
    "sector-rotation": SectorRotationStrategy,
    "dividend-harvest": DividendHarvestStrategy,
    "trend-following": TrendFollowingStrategy,
    "breakout": BreakoutStrategy,
    "mean-reversion-bb": MeanReversionBBStrategy,
    "multi-factor": MultiFactorStrategy,
    "btc-cycle": BTCCycleIndicator,
}


def get_strategy(name: str) -> type["Strategy"]:
    """Get a strategy class by its slug name."""
    if name not in STRATEGY_REGISTRY:
        raise KeyError(f"Unknown strategy '{name}'. Available: {list(STRATEGY_REGISTRY.keys())}")
    return STRATEGY_REGISTRY[name]


def list_strategies() -> list[StrategyMeta]:
    """Return metadata for all built-in strategies."""
    return [cls.meta() for cls in STRATEGY_REGISTRY.values()]


__all__ = [
    "Strategy", "StrategySignal", "StrategyMeta",
    "GridTradingStrategy", "FundingRateArbitrage", "DCAStrategy",
    "PairsTradingStrategy", "SectorRotationStrategy", "DividendHarvestStrategy",
    "TrendFollowingStrategy", "BreakoutStrategy", "MeanReversionBBStrategy",
    "MultiFactorStrategy",
    "BTCCycleIndicator",
    "STRATEGY_REGISTRY", "get_strategy", "list_strategies",
]
