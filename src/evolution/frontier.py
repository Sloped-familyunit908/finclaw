"""
Frontier — maintain top-N best strategies with lineage tracking.

Inspired by EvoSkill's (μ+λ) evolutionary strategy, the frontier
keeps a fixed-size collection of the best-performing strategy variants
and supports parent selection for the next evolution iteration.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from typing import Any

from .evaluator import FitnessScore


@dataclass
class FrontierEntry:
    """A single strategy in the frontier."""

    strategy_yaml: str
    score: FitnessScore
    generation: int
    parent_id: str | None = None
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "generation": self.generation,
            "parent_id": self.parent_id,
            "score": self.score.to_dict(),
            "strategy_yaml": self.strategy_yaml,
        }


class Frontier:
    """Fixed-size frontier of top-performing strategies.

    Parameters
    ----------
    max_size:
        Maximum number of strategies to keep.  When a new entry is
        added that would exceed this, the worst is evicted.
    """

    def __init__(self, max_size: int = 3) -> None:
        self.max_size = max_size
        self._entries: list[FrontierEntry] = []
        # Keep evicted entries for lineage tracking
        self._all_entries: dict[str, FrontierEntry] = {}

    # -- properties --

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def entries(self) -> list[FrontierEntry]:
        """Return entries sorted by composite score (descending)."""
        return sorted(self._entries, key=lambda e: e.score.composite(), reverse=True)

    @property
    def best(self) -> FrontierEntry:
        """Return the highest-scoring entry."""
        if not self._entries:
            raise ValueError("Frontier is empty")
        return max(self._entries, key=lambda e: e.score.composite())

    # -- mutation --

    def update(
        self,
        strategy_yaml: str,
        score: FitnessScore,
        generation: int,
        parent_id: str | None = None,
    ) -> FrontierEntry | None:
        """Try to add a strategy to the frontier.

        Returns the created :class:`FrontierEntry` if accepted, or
        ``None`` if the strategy was worse than all current entries
        and the frontier is already full.
        """
        entry = FrontierEntry(
            strategy_yaml=strategy_yaml,
            score=score,
            generation=generation,
            parent_id=parent_id,
        )

        if len(self._entries) < self.max_size:
            self._entries.append(entry)
            self._all_entries[entry.entry_id] = entry
            return entry

        # Find worst current entry
        worst = min(self._entries, key=lambda e: e.score.composite())
        if score.composite() > worst.score.composite():
            self._entries.remove(worst)
            self._entries.append(entry)
            self._all_entries[entry.entry_id] = entry
            return entry

        return None  # Rejected

    # -- selection --

    def select_parent(self, strategy: str = "best") -> FrontierEntry:
        """Select a parent strategy for the next mutation.

        Strategies:
          - ``"best"``: Always pick the highest-scoring entry.
          - ``"random"``: Uniform random from frontier.
          - ``"round_robin"``: Cycle through entries by rank.
        """
        if not self._entries:
            raise ValueError("Cannot select from an empty frontier")

        if strategy == "best":
            return self.best
        elif strategy == "random":
            return random.choice(self._entries)
        elif strategy == "round_robin":
            # Simple round-robin: rotate through sorted entries
            sorted_entries = self.entries
            if not hasattr(self, "_rr_index"):
                self._rr_index = 0
            idx = self._rr_index % len(sorted_entries)
            self._rr_index += 1
            return sorted_entries[idx]
        else:
            raise ValueError(f"Unknown selection strategy: {strategy}")

    # -- lineage --

    def get_lineage(self, entry_id: str) -> list[FrontierEntry]:
        """Trace the ancestral chain of a strategy.

        Returns a list starting from the given entry back to the
        earliest known ancestor.
        """
        lineage: list[FrontierEntry] = []
        current_id: str | None = entry_id
        visited: set[str] = set()

        while current_id and current_id not in visited:
            visited.add(current_id)
            entry = self._all_entries.get(current_id)
            if entry is None:
                break
            lineage.append(entry)
            current_id = entry.parent_id

        return lineage

    # -- serialization --

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_size": self.max_size,
            "entries": [e.to_dict() for e in self.entries],
        }
