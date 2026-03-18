"""FinClaw Strategy DSL Engine v2.0.0

**This module is the YAML Strategy DSL engine** — it parses and evaluates
strategy definitions written in YAML.

For concrete Python strategy implementations (MeanReversion, Momentum,
TrendFollowing, etc.), import from ``src.strategies`` instead.

Summary:
  - ``src.strategy``    → YAML DSL engine (parse, evaluate, optimize YAML strategies)
  - ``src.strategies``  → Concrete strategy library (Python classes)
"""

from .dsl import StrategyDSL, Strategy
from .expression import ExpressionEvaluator
from .library import BUILTIN_STRATEGIES, get_strategy, list_strategies
from .optimizer import StrategyOptimizer

__all__ = [
    "StrategyDSL",
    "Strategy",
    "ExpressionEvaluator",
    "BUILTIN_STRATEGIES",
    "get_strategy",
    "list_strategies",
    "StrategyOptimizer",
]
