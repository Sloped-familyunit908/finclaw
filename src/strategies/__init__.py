"""FinClaw Strategy Templates v1.2.0"""
from .mean_reversion import MeanReversionStrategy
from .momentum_jt import MomentumJTStrategy
from .pairs_trading import PairsTradingStrategy
from .trend_following import TrendFollowingStrategy
from .value_momentum import ValueMomentumStrategy

__all__ = [
    "MeanReversionStrategy",
    "MomentumJTStrategy",
    "PairsTradingStrategy",
    "TrendFollowingStrategy",
    "ValueMomentumStrategy",
]
