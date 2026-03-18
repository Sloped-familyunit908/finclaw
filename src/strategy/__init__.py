"""
DEPRECATED: Use `src.strategies` for strategy templates, or `src.strategy` for the YAML DSL.

This module (`src.strategy`) contains the YAML Strategy DSL engine. It is NOT deprecated,
but if you're looking for strategy templates (MeanReversion, Momentum, TrendFollowing, etc.),
use `src.strategies` instead.

The two modules serve different purposes:
  - `src.strategy` → YAML DSL: parse and evaluate strategy definitions written in YAML
  - `src.strategies` → Strategy library: concrete Python strategy implementations

This note clarifies the naming overlap for developers.
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
