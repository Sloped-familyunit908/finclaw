"""FinClaw Strategy Templates v1.3.0"""
from .mean_reversion import MeanReversionStrategy
from .momentum_jt import MomentumJTStrategy
from .pairs_trading import PairsTradingStrategy
from .trend_following import TrendFollowingStrategy
from .value_momentum import ValueMomentumStrategy
from .combiner import StrategyCombiner, MeanReversionAdapter, MomentumAdapter, TrendFollowingAdapter, ValueMomentumAdapter
from .sector_rotation import SectorRotation, SectorSignal
from .signal_combiner import SignalCombiner, CombinedSignal
from .regime_adaptive import RegimeAdaptive, RegimeSignal

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
    "SectorRotation",
    "SectorSignal",
    "SignalCombiner",
    "CombinedSignal",
    "RegimeAdaptive",
    "RegimeSignal",
]
