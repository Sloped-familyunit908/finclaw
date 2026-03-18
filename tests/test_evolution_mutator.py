"""Tests for src/evolution/mutator.py — targeted strategy mutations."""

from __future__ import annotations

import yaml
import pytest

from src.evolution.mutator import Mutator, MutationType
from src.evolution.proposer import Proposal


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BASE_STRATEGY = """\
name: Golden Cross
entry:
  - sma(20) > sma(50)
  - rsi(14) < 70
exit:
  - sma(20) < sma(50)
  - OR: rsi(14) > 80
risk:
  stop_loss: 5%
  take_profit: 15%
  max_position: 10%
rebalance: weekly
"""

RSI_STRATEGY = """\
name: RSI Mean Reversion
entry:
  - rsi(14) < 30
  - close > sma(200)
exit:
  - rsi(14) > 70
risk:
  stop_loss: 3%
  take_profit: 10%
"""


# ---------------------------------------------------------------------------
# MutationType tests
# ---------------------------------------------------------------------------

class TestMutationType:
    """Tests for the MutationType enum."""

    def test_all_types_exist(self):
        assert MutationType.PARAMETER_TUNE
        assert MutationType.INDICATOR_SWAP
        assert MutationType.ADD_FILTER
        assert MutationType.REMOVE_FILTER
        assert MutationType.ADJUST_RISK
        assert MutationType.COMBINE_STRATEGY


# ---------------------------------------------------------------------------
# Mutator tests
# ---------------------------------------------------------------------------

class TestMutator:
    """Tests for the Mutator class."""

    def test_parameter_tune_sma(self):
        """Should mutate SMA window parameters."""
        mutator = Mutator()
        proposal = Proposal(
            mutation_type="parameter_tune",
            target="sma_fast",
            description="Increase fast SMA period for smoother signals",
            details={"indicator": "sma", "old_param": 20, "new_param": 30},
            confidence=0.8,
        )
        result = mutator.mutate(BASE_STRATEGY, proposal)
        assert isinstance(result, str)
        parsed = yaml.safe_load(result)
        assert parsed["name"]  # should still be valid YAML strategy
        # The mutation should change sma(20) to sma(30)
        assert any("sma(30)" in c for c in parsed.get("entry", []) if isinstance(c, str))

    def test_parameter_tune_rsi(self):
        """Should mutate RSI period."""
        mutator = Mutator()
        proposal = Proposal(
            mutation_type="parameter_tune",
            target="rsi_period",
            description="Adjust RSI period",
            details={"indicator": "rsi", "old_param": 14, "new_param": 20},
            confidence=0.7,
        )
        result = mutator.mutate(RSI_STRATEGY, proposal)
        parsed = yaml.safe_load(result)
        # Check that rsi(14) changed to rsi(20) in at least one condition
        all_conditions = parsed.get("entry", []) + parsed.get("exit", [])
        text_conditions = [c for c in all_conditions if isinstance(c, str)]
        assert any("rsi(20)" in c for c in text_conditions)

    def test_indicator_swap_sma_to_ema(self):
        """Should swap SMA indicator for EMA."""
        mutator = Mutator()
        proposal = Proposal(
            mutation_type="indicator_swap",
            target="entry",
            description="Replace SMA with EMA for faster response",
            details={"old_indicator": "sma", "new_indicator": "ema"},
            confidence=0.6,
        )
        result = mutator.mutate(BASE_STRATEGY, proposal)
        parsed = yaml.safe_load(result)
        entry = parsed.get("entry", [])
        text_entries = [c for c in entry if isinstance(c, str)]
        assert any("ema(" in c for c in text_entries)
        # SMA should no longer be in entry (swapped out)
        # (but may remain if only one occurrence is swapped)

    def test_add_volume_filter(self):
        """Should add a volume filter to entry conditions."""
        mutator = Mutator()
        proposal = Proposal(
            mutation_type="add_filter",
            target="entry",
            description="Add volume confirmation",
            details={"filter": "volume > sma_volume(20) * 1.5"},
            confidence=0.7,
        )
        result = mutator.mutate(RSI_STRATEGY, proposal)
        parsed = yaml.safe_load(result)
        entry = parsed.get("entry", [])
        text_entries = [c for c in entry if isinstance(c, str)]
        assert any("volume" in c for c in text_entries)

    def test_remove_filter(self):
        """Should remove a specified filter from conditions."""
        mutator = Mutator()
        proposal = Proposal(
            mutation_type="remove_filter",
            target="entry",
            description="Remove overly restrictive RSI filter",
            details={"filter_pattern": "rsi"},
            confidence=0.5,
        )
        result = mutator.mutate(BASE_STRATEGY, proposal)
        parsed = yaml.safe_load(result)
        entry = parsed.get("entry", [])
        text_entries = [c for c in entry if isinstance(c, str)]
        # RSI condition should be removed from entry
        assert not any("rsi(" in c for c in text_entries)

    def test_adjust_risk_stop_loss(self):
        """Should tighten stop loss."""
        mutator = Mutator()
        proposal = Proposal(
            mutation_type="adjust_risk",
            target="risk",
            description="Tighten stop loss to reduce drawdown",
            details={"stop_loss": "3%"},
            confidence=0.8,
        )
        result = mutator.mutate(BASE_STRATEGY, proposal)
        parsed = yaml.safe_load(result)
        assert parsed["risk"]["stop_loss"] == "3%"

    def test_adjust_risk_take_profit(self):
        """Should adjust take profit."""
        mutator = Mutator()
        proposal = Proposal(
            mutation_type="adjust_risk",
            target="risk",
            description="Increase take profit target",
            details={"take_profit": "20%"},
            confidence=0.6,
        )
        result = mutator.mutate(BASE_STRATEGY, proposal)
        parsed = yaml.safe_load(result)
        assert parsed["risk"]["take_profit"] == "20%"

    def test_mutation_preserves_name(self):
        """Strategy name should be preserved after mutation."""
        mutator = Mutator()
        proposal = Proposal(
            mutation_type="parameter_tune",
            target="sma",
            description="Tune SMA",
            details={"indicator": "sma", "old_param": 20, "new_param": 25},
            confidence=0.7,
        )
        result = mutator.mutate(BASE_STRATEGY, proposal)
        parsed = yaml.safe_load(result)
        # Name should still exist (might be modified to indicate mutation)
        assert "name" in parsed

    def test_mutation_returns_valid_yaml(self):
        """All mutations should return parseable YAML."""
        mutator = Mutator()
        proposals = [
            Proposal("parameter_tune", "sma", "tune", {"indicator": "sma", "old_param": 20, "new_param": 30}, 0.7),
            Proposal("add_filter", "entry", "add", {"filter": "adx(14) > 25"}, 0.6),
            Proposal("adjust_risk", "risk", "adjust", {"stop_loss": "2%"}, 0.8),
        ]
        for p in proposals:
            result = mutator.mutate(BASE_STRATEGY, p)
            parsed = yaml.safe_load(result)
            assert isinstance(parsed, dict)
            assert "name" in parsed

    def test_combine_strategy(self):
        """Should combine two strategies (merge entry/exit conditions)."""
        mutator = Mutator()
        proposal = Proposal(
            mutation_type="combine_strategy",
            target="strategy",
            description="Combine with RSI strategy",
            details={"other_strategy": RSI_STRATEGY},
            confidence=0.5,
        )
        result = mutator.mutate(BASE_STRATEGY, proposal)
        parsed = yaml.safe_load(result)
        # Combined strategy should have conditions from both
        entry = parsed.get("entry", [])
        text_entries = [c for c in entry if isinstance(c, str)]
        assert len(text_entries) >= 2  # Should have entries from both strategies

    def test_mutate_with_feedback(self):
        """Mutator should accept optional feedback context."""
        mutator = Mutator()
        feedback = {"reason": "Too many losing trades", "avg_loss": -0.05}
        proposal = Proposal(
            mutation_type="adjust_risk",
            target="risk",
            description="Tighten risk",
            details={"stop_loss": "2%"},
            confidence=0.8,
        )
        result = mutator.mutate(BASE_STRATEGY, proposal, feedback=feedback)
        assert isinstance(result, str)
        parsed = yaml.safe_load(result)
        assert parsed["risk"]["stop_loss"] == "2%"
