"""FinClaw Strategy Evolution Engine v1.0.0

EvoSkill-inspired automatic strategy evolution from backtest failures.

Evolves YAML-DSL trading strategies through an iterative loop:
  evaluate → analyze failures → propose mutations → select best

Core components:
  - Evaluator: Backtest a strategy and compute fitness scores
  - Proposer: Analyze failed backtests and propose improvements
  - Mutator: Apply targeted mutations to strategy YAML configs
  - Frontier: Maintain top-N strategies with lineage tracking
  - Engine: The main evolution loop
  - CLI: ``finclaw evolve`` command
"""

from .evaluator import Evaluator, FitnessScore
from .proposer import Proposer, FailureAnalysis, Proposal
from .mutator import Mutator, MutationType
from .frontier import Frontier, FrontierEntry
from .engine import EvolutionEngine, EvolutionConfig

__all__ = [
    "Evaluator",
    "FitnessScore",
    "Proposer",
    "FailureAnalysis",
    "Proposal",
    "Mutator",
    "MutationType",
    "Frontier",
    "FrontierEntry",
    "EvolutionEngine",
    "EvolutionConfig",
]
