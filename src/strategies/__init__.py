"""
FinClaw Strategy Templates v1.3.0

This is the primary strategy module containing concrete Python strategy implementations.
For the YAML Strategy DSL engine, see `src.strategy`.

Module distinction:
  - `src.strategies` (this module) → Concrete strategy classes (MeanReversion, Momentum, etc.)
  - `src.strategy` → YAML DSL engine for defining strategies in YAML
"""
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
