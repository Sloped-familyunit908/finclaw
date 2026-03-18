"""Tests for src/evolution/frontier.py — top-N strategy selection with lineage."""

from __future__ import annotations

import pytest

from src.evolution.frontier import Frontier, FrontierEntry
from src.evolution.evaluator import FitnessScore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _score(sharpe: float = 1.0, ret: float = 0.2, dd: float = -0.1,
           wr: float = 0.6, trades: int = 20) -> FitnessScore:
    return FitnessScore(
        sharpe_ratio=sharpe,
        total_return=ret,
        max_drawdown=dd,
        win_rate=wr,
        total_trades=trades,
    )


STRATEGY_A = """\
name: Strategy A
entry:
  - sma(20) > sma(50)
exit:
  - sma(20) < sma(50)
risk:
  stop_loss: 5%
"""

STRATEGY_B = """\
name: Strategy B
entry:
  - rsi(14) < 30
exit:
  - rsi(14) > 70
risk:
  stop_loss: 3%
"""

STRATEGY_C = """\
name: Strategy C
entry:
  - ema(10) > ema(30)
exit:
  - ema(10) < ema(30)
risk:
  stop_loss: 4%
"""


# ---------------------------------------------------------------------------
# FrontierEntry tests
# ---------------------------------------------------------------------------

class TestFrontierEntry:
    """Tests for the FrontierEntry dataclass."""

    def test_creation(self):
        entry = FrontierEntry(
            strategy_yaml=STRATEGY_A,
            score=_score(1.5, 0.3, -0.08, 0.65, 25),
            generation=0,
            parent_id=None,
        )
        assert entry.strategy_yaml == STRATEGY_A
        assert entry.score.sharpe_ratio == 1.5
        assert entry.generation == 0
        assert entry.parent_id is None

    def test_has_id(self):
        """Each entry should have a unique identifier."""
        entry = FrontierEntry(
            strategy_yaml=STRATEGY_A,
            score=_score(),
            generation=0,
        )
        assert entry.entry_id  # Should auto-generate an ID
        assert isinstance(entry.entry_id, str)

    def test_unique_ids(self):
        """Different entries should have different IDs."""
        e1 = FrontierEntry(strategy_yaml=STRATEGY_A, score=_score(), generation=0)
        e2 = FrontierEntry(strategy_yaml=STRATEGY_B, score=_score(), generation=0)
        assert e1.entry_id != e2.entry_id


# ---------------------------------------------------------------------------
# Frontier tests
# ---------------------------------------------------------------------------

class TestFrontier:
    """Tests for the Frontier class."""

    def test_creation_with_max_size(self):
        frontier = Frontier(max_size=5)
        assert frontier.max_size == 5
        assert len(frontier) == 0

    def test_add_entry(self):
        frontier = Frontier(max_size=3)
        entry = frontier.update(STRATEGY_A, _score(1.0), generation=0)
        assert len(frontier) == 1
        assert isinstance(entry, FrontierEntry)

    def test_respects_max_size(self):
        """Frontier should not exceed max_size."""
        frontier = Frontier(max_size=2)
        frontier.update(STRATEGY_A, _score(1.0), generation=0)
        frontier.update(STRATEGY_B, _score(2.0), generation=1)
        frontier.update(STRATEGY_C, _score(3.0), generation=2)
        assert len(frontier) == 2

    def test_evicts_worst(self):
        """When full, adding a better strategy should evict the worst."""
        frontier = Frontier(max_size=2)
        frontier.update(STRATEGY_A, _score(sharpe=1.0, ret=0.1), generation=0)
        frontier.update(STRATEGY_B, _score(sharpe=2.0, ret=0.3), generation=1)
        # Add a strategy better than A
        frontier.update(STRATEGY_C, _score(sharpe=3.0, ret=0.5), generation=2)
        assert len(frontier) == 2
        names = [e.strategy_yaml for e in frontier.entries]
        # A (worst) should be evicted
        assert STRATEGY_A not in names
        assert STRATEGY_B in names or STRATEGY_C in names

    def test_does_not_add_worse_than_worst(self):
        """When full, a strategy worse than the worst should be rejected."""
        frontier = Frontier(max_size=2)
        frontier.update(STRATEGY_A, _score(sharpe=2.0, ret=0.3), generation=0)
        frontier.update(STRATEGY_B, _score(sharpe=3.0, ret=0.5), generation=1)
        # Try to add a worse strategy
        result = frontier.update(STRATEGY_C, _score(sharpe=0.1, ret=-0.1), generation=2)
        assert len(frontier) == 2
        assert result is None  # Should be rejected

    def test_select_parent_best(self):
        """select_parent('best') should return the highest-scoring entry."""
        frontier = Frontier(max_size=3)
        frontier.update(STRATEGY_A, _score(sharpe=1.0), generation=0)
        frontier.update(STRATEGY_B, _score(sharpe=3.0), generation=1)
        frontier.update(STRATEGY_C, _score(sharpe=2.0), generation=2)
        best = frontier.select_parent(strategy="best")
        assert best.score.sharpe_ratio == 3.0

    def test_select_parent_random(self):
        """select_parent('random') should return an entry."""
        frontier = Frontier(max_size=3)
        frontier.update(STRATEGY_A, _score(), generation=0)
        frontier.update(STRATEGY_B, _score(), generation=1)
        result = frontier.select_parent(strategy="random")
        assert isinstance(result, FrontierEntry)

    def test_select_parent_empty_raises(self):
        """Selecting from an empty frontier should raise."""
        frontier = Frontier(max_size=3)
        with pytest.raises(ValueError):
            frontier.select_parent()

    def test_lineage_tracking(self):
        """Child entries should reference their parent."""
        frontier = Frontier(max_size=5)
        parent = frontier.update(STRATEGY_A, _score(sharpe=1.0), generation=0)
        child = frontier.update(STRATEGY_B, _score(sharpe=2.0), generation=1,
                                parent_id=parent.entry_id)
        assert child.parent_id == parent.entry_id

    def test_get_lineage(self):
        """Should trace the lineage chain of a strategy."""
        frontier = Frontier(max_size=5)
        gen0 = frontier.update(STRATEGY_A, _score(sharpe=1.0), generation=0)
        gen1 = frontier.update(STRATEGY_B, _score(sharpe=2.0), generation=1,
                               parent_id=gen0.entry_id)
        gen2 = frontier.update(STRATEGY_C, _score(sharpe=3.0), generation=2,
                               parent_id=gen1.entry_id)
        lineage = frontier.get_lineage(gen2.entry_id)
        assert len(lineage) >= 2  # At least gen2 and gen1

    def test_best_property(self):
        """frontier.best should return the top entry."""
        frontier = Frontier(max_size=3)
        frontier.update(STRATEGY_A, _score(sharpe=1.0), generation=0)
        frontier.update(STRATEGY_B, _score(sharpe=5.0), generation=1)
        assert frontier.best.score.sharpe_ratio == 5.0

    def test_entries_sorted(self):
        """frontier.entries should be sorted by composite score descending."""
        frontier = Frontier(max_size=5)
        frontier.update(STRATEGY_A, _score(sharpe=1.0, ret=0.1), generation=0)
        frontier.update(STRATEGY_B, _score(sharpe=3.0, ret=0.4), generation=1)
        frontier.update(STRATEGY_C, _score(sharpe=2.0, ret=0.2), generation=2)
        entries = frontier.entries
        scores = [e.score.composite() for e in entries]
        assert scores == sorted(scores, reverse=True)

    def test_to_dict(self):
        """Frontier should be serializable."""
        frontier = Frontier(max_size=3)
        frontier.update(STRATEGY_A, _score(), generation=0)
        d = frontier.to_dict()
        assert "entries" in d
        assert "max_size" in d
        assert len(d["entries"]) == 1
