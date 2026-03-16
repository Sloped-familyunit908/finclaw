"""FinClaw Strategy Templates v1.3.0"""
from .mean_reversion import MeanReversionStrategy
from .momentum_jt import MomentumJTStrategy
from .pairs_trading import PairsTradingStrategy
from .trend_following import TrendFollowingStrategy
from .value_momentum import ValueMomentumStrategy
from .combiner import StrategyCombiner, MeanReversionAdapter, MomentumAdapter, TrendFollowingAdapter, ValueMomentumAdapter

__all__ = [
    "MeanReversionStrategy",
    "MomentumJTStrategy",
    "PairsTradingStrategy",
    "TrendFollowingStrategy",
    "ValueMomentumStrategy",
    "StrategyCombiner",
    "MeanReversionAdapter",
    "MomentumAdapter",
    "TrendFollowingAdapter",
    "ValueMomentumAdapter",
]
