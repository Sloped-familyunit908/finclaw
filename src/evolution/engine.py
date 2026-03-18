"""
EvolutionEngine — the main self-improving loop.

Inspired by EvoSkill's architecture:
  1. Evaluate seed strategy → add to frontier
  2. Select parent from frontier
  3. Evaluate parent → analyze failures → propose mutations
  4. Mutate strategy → evaluate child
  5. Update frontier (accept if better than worst)
  6. Repeat until max_generations or early-stop
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from src.strategy.expression import OHLCVData

from .evaluator import Evaluator, FitnessScore
from .proposer import Proposer
from .mutator import Mutator
from .frontier import Frontier


@dataclass
class EvolutionConfig:
    """Hyperparameters for the evolution loop."""

    max_generations: int = 10
    frontier_size: int = 3
    no_improvement_limit: int = 5


@dataclass
class _HistoryEntry:
    """Record of a single generation."""

    generation: int
    parent_id: str | None
    child_id: str | None
    child_score: float
    accepted: bool
    mutation_type: str = ""
    mutation_desc: str = ""


class EvolutionEngine:
    """Run the evolutionary strategy improvement loop.

    Parameters
    ----------
    config:
        Evolution hyperparameters.
    evaluator, proposer, mutator, frontier:
        Optional custom component instances. If ``None`` the engine
        creates defaults.
    """

    def __init__(
        self,
        config: EvolutionConfig | None = None,
        evaluator: Evaluator | None = None,
        proposer: Proposer | None = None,
        mutator: Mutator | None = None,
        frontier: Frontier | None = None,
    ) -> None:
        self.config = config or EvolutionConfig()
        self.evaluator = evaluator or Evaluator()
        self.proposer = proposer or Proposer()
        self.mutator = mutator or Mutator()
        if frontier is not None:
            self.frontier = frontier
        else:
            self.frontier = Frontier(max_size=self.config.frontier_size)

    def run(
        self,
        seed_strategy: str,
        data: OHLCVData,
        *,
        on_generation: Callable[[int, FitnessScore, str], Any] | None = None,
    ) -> dict[str, Any]:
        """Execute the evolution loop.

        Parameters
        ----------
        seed_strategy:
            Initial strategy YAML to evolve.
        data:
            Historical OHLCV data for backtesting.
        on_generation:
            Optional callback ``(gen_number, score, strategy_yaml)``
            called after each generation.

        Returns
        -------
        dict with keys:
            - ``best_strategy``: YAML of the best strategy found.
            - ``best_score``: :class:`FitnessScore` of the best.
            - ``generations_run``: How many generations completed.
            - ``history``: List of per-generation records.
        """
        history: list[_HistoryEntry] = []
        no_improvement_count = 0
        best_composite = float("-inf")

        # ---- Step 0: Evaluate and add seed ----
        seed_score = self.evaluator.evaluate(seed_strategy, data)
        seed_entry = self.frontier.update(seed_strategy, seed_score, generation=0)
        best_composite = seed_score.composite()

        if on_generation:
            on_generation(0, seed_score, seed_strategy)

        history.append(_HistoryEntry(
            generation=0,
            parent_id=None,
            child_id=seed_entry.entry_id if seed_entry else None,
            child_score=seed_score.composite(),
            accepted=True,
            mutation_type="seed",
            mutation_desc="Initial strategy",
        ))

        # ---- Main loop ----
        generations_run = 0
        for gen in range(1, self.config.max_generations + 1):
            generations_run = gen

            # 1. Select parent
            parent = self.frontier.select_parent(strategy="best")

            # 2. Evaluate parent (may re-evaluate, but uses cached feedback)
            parent_score = self.evaluator.evaluate(parent.strategy_yaml, data)
            feedback = self.evaluator.last_feedback

            # 3. Analyze failures
            analyses = self.proposer.analyze(parent.strategy_yaml, feedback)
            if not analyses:
                # No failures detected → skip
                no_improvement_count += 1
                if no_improvement_count >= self.config.no_improvement_limit:
                    break
                continue

            # 4. Propose improvements
            proposals = self.proposer.propose(parent.strategy_yaml, analyses)
            if not proposals:
                no_improvement_count += 1
                if no_improvement_count >= self.config.no_improvement_limit:
                    break
                continue

            # 5. Try the best proposal (highest confidence)
            proposals.sort(key=lambda p: p.confidence, reverse=True)
            proposal = proposals[0]

            try:
                mutated_yaml = self.mutator.mutate(
                    parent.strategy_yaml,
                    proposal,
                    feedback=feedback,
                )
            except Exception:
                no_improvement_count += 1
                if no_improvement_count >= self.config.no_improvement_limit:
                    break
                continue

            # 6. Evaluate child
            try:
                child_score = self.evaluator.evaluate(mutated_yaml, data)
            except Exception:
                no_improvement_count += 1
                if no_improvement_count >= self.config.no_improvement_limit:
                    break
                continue

            # 7. Update frontier
            child_entry = self.frontier.update(
                mutated_yaml,
                child_score,
                generation=gen,
                parent_id=parent.entry_id,
            )
            accepted = child_entry is not None

            if child_score.composite() > best_composite:
                best_composite = child_score.composite()
                no_improvement_count = 0
            else:
                no_improvement_count += 1

            history.append(_HistoryEntry(
                generation=gen,
                parent_id=parent.entry_id,
                child_id=child_entry.entry_id if child_entry else None,
                child_score=child_score.composite(),
                accepted=accepted,
                mutation_type=proposal.mutation_type,
                mutation_desc=proposal.description,
            ))

            if on_generation:
                on_generation(gen, child_score, mutated_yaml)

            if no_improvement_count >= self.config.no_improvement_limit:
                break

        # ---- Return results ----
        best = self.frontier.best
        return {
            "best_strategy": best.strategy_yaml,
            "best_score": best.score,
            "generations_run": generations_run,
            "history": [
                {
                    "generation": h.generation,
                    "parent_id": h.parent_id,
                    "child_id": h.child_id,
                    "child_score": h.child_score,
                    "accepted": h.accepted,
                    "mutation_type": h.mutation_type,
                    "mutation_desc": h.mutation_desc,
                }
                for h in history
            ],
        }
