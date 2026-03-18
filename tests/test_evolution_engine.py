"""Tests for src/evolution/engine.py — the main evolution loop."""

from __future__ import annotations

import numpy as np
import pytest

from src.evolution.engine import EvolutionEngine, EvolutionConfig
from src.evolution.evaluator import Evaluator, FitnessScore
from src.evolution.proposer import Proposer
from src.evolution.mutator import Mutator
from src.evolution.frontier import Frontier
from src.strategy.expression import OHLCVData


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_ohlcv(closes: list[float]) -> OHLCVData:
    n = len(closes)
    c = np.array(closes, dtype=np.float64)
    return OHLCVData(
        open=c * 0.99,
        high=c * 1.01,
        low=c * 0.98,
        close=c,
        volume=np.full(n, 1_000_000, dtype=np.float64),
    )


def _trending_data(n: int = 300) -> OHLCVData:
    closes = [100.0]
    for _ in range(n - 1):
        closes.append(closes[-1] * 1.002)
    return _make_ohlcv(closes)


SEED_STRATEGY = """\
name: Seed Strategy
entry:
  - sma(20) > sma(50)
  - rsi(14) < 70
exit:
  - sma(20) < sma(50)
risk:
  stop_loss: 5%
  take_profit: 15%
"""


# ---------------------------------------------------------------------------
# EvolutionConfig tests
# ---------------------------------------------------------------------------

class TestEvolutionConfig:
    """Tests for the EvolutionConfig dataclass."""

    def test_defaults(self):
        config = EvolutionConfig()
        assert config.max_generations > 0
        assert config.frontier_size > 0
        assert config.no_improvement_limit > 0

    def test_custom_values(self):
        config = EvolutionConfig(
            max_generations=50,
            frontier_size=5,
            no_improvement_limit=10,
        )
        assert config.max_generations == 50
        assert config.frontier_size == 5
        assert config.no_improvement_limit == 10


# ---------------------------------------------------------------------------
# EvolutionEngine tests
# ---------------------------------------------------------------------------

class TestEvolutionEngine:
    """Tests for the EvolutionEngine class."""

    def test_creation(self):
        engine = EvolutionEngine(config=EvolutionConfig(max_generations=3))
        assert engine.config.max_generations == 3
        assert isinstance(engine.evaluator, Evaluator)
        assert isinstance(engine.proposer, Proposer)
        assert isinstance(engine.mutator, Mutator)
        assert isinstance(engine.frontier, Frontier)

    def test_custom_components(self):
        """Should accept custom components via constructor."""
        evaluator = Evaluator()
        proposer = Proposer()
        mutator = Mutator()
        frontier = Frontier(max_size=5)
        engine = EvolutionEngine(
            config=EvolutionConfig(max_generations=3, frontier_size=5),
            evaluator=evaluator,
            proposer=proposer,
            mutator=mutator,
            frontier=frontier,
        )
        assert engine.evaluator is evaluator
        assert engine.proposer is proposer
        assert engine.mutator is mutator
        assert engine.frontier is frontier

    def test_run_returns_result(self):
        """Engine.run should return the best strategy and its score."""
        engine = EvolutionEngine(config=EvolutionConfig(
            max_generations=2,
            frontier_size=3,
            no_improvement_limit=3,
        ))
        data = _trending_data(300)
        result = engine.run(SEED_STRATEGY, data)
        assert "best_strategy" in result
        assert "best_score" in result
        assert "generations_run" in result
        assert isinstance(result["best_score"], FitnessScore)
        assert isinstance(result["best_strategy"], str)

    def test_seed_strategy_in_frontier(self):
        """After run, the seed strategy should have been in the frontier at gen 0."""
        engine = EvolutionEngine(config=EvolutionConfig(
            max_generations=1,
            frontier_size=3,
            no_improvement_limit=3,
        ))
        data = _trending_data(300)
        engine.run(SEED_STRATEGY, data)
        # The frontier should have at least one entry
        assert len(engine.frontier) >= 1

    def test_history_tracked(self):
        """Engine should track evolution history."""
        engine = EvolutionEngine(config=EvolutionConfig(
            max_generations=2,
            frontier_size=3,
            no_improvement_limit=3,
        ))
        data = _trending_data(300)
        result = engine.run(SEED_STRATEGY, data)
        assert "history" in result
        assert isinstance(result["history"], list)
        assert len(result["history"]) >= 1

    def test_early_stop_on_no_improvement(self):
        """Should stop early when no improvement for N generations."""
        engine = EvolutionEngine(config=EvolutionConfig(
            max_generations=100,  # Very high
            frontier_size=3,
            no_improvement_limit=2,  # Stop after 2 stagnant gens
        ))
        data = _trending_data(300)
        result = engine.run(SEED_STRATEGY, data)
        # Should have stopped before 100 generations
        assert result["generations_run"] < 100

    def test_best_strategy_valid_yaml(self):
        """Best strategy should be parseable YAML."""
        import yaml
        engine = EvolutionEngine(config=EvolutionConfig(
            max_generations=2,
            frontier_size=3,
            no_improvement_limit=3,
        ))
        data = _trending_data(300)
        result = engine.run(SEED_STRATEGY, data)
        parsed = yaml.safe_load(result["best_strategy"])
        assert isinstance(parsed, dict)
        assert "name" in parsed
        assert "entry" in parsed

    def test_callbacks(self):
        """Should call on_generation callback if provided."""
        calls = []

        def on_gen(gen_num, score, strategy):
            calls.append(gen_num)

        engine = EvolutionEngine(config=EvolutionConfig(
            max_generations=2,
            frontier_size=3,
            no_improvement_limit=3,
        ))
        data = _trending_data(300)
        engine.run(SEED_STRATEGY, data, on_generation=on_gen)
        assert len(calls) >= 1
