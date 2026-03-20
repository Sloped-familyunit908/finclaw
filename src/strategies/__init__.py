"""FinClaw Strategy Library v2.0.0

**This module is the concrete strategy library** — Python strategy classes
for mean reversion, momentum, trend following, pairs trading, etc.

For the YAML Strategy DSL engine (parsing strategy definitions from YAML),
import from ``src.strategy`` instead.

Summary:
  - ``src.strategies``  → Concrete strategy library (Python classes) ← YOU ARE HERE
  - ``src.strategy``    → YAML DSL engine (parse, evaluate, optimize YAML strategies)
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
from .trend_discovery import TrendDiscovery, TrendCandidate

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
    "TrendDiscovery",
    "TrendCandidate",
]
