"""Tests for src/evolution/proposer.py — failure analysis and improvement proposals."""

from __future__ import annotations

import pytest

from src.evolution.proposer import Proposer, FailureAnalysis, Proposal
from src.evolution.evaluator import FitnessScore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

STRATEGY_YAML = """\
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

LOW_RETURN_FEEDBACK = {
    "score": {
        "sharpe_ratio": 0.1,
        "total_return": -0.05,
        "max_drawdown": -0.08,
        "win_rate": 0.40,
        "total_trades": 5,
    },
    "trade_count": 5,
    "winning_trades": 2,
    "losing_trades": 3,
    "avg_win": 0.02,
    "avg_loss": -0.04,
    "periods": 300,
}

HIGH_DRAWDOWN_FEEDBACK = {
    "score": {
        "sharpe_ratio": 0.5,
        "total_return": 0.15,
        "max_drawdown": -0.35,
        "win_rate": 0.55,
        "total_trades": 20,
    },
    "trade_count": 20,
    "winning_trades": 11,
    "losing_trades": 9,
    "avg_win": 0.03,
    "avg_loss": -0.05,
    "periods": 300,
}

FEW_TRADES_FEEDBACK = {
    "score": {
        "sharpe_ratio": 0.0,
        "total_return": 0.0,
        "max_drawdown": 0.0,
        "win_rate": 0.0,
        "total_trades": 0,
    },
    "trade_count": 0,
    "winning_trades": 0,
    "losing_trades": 0,
    "avg_win": 0.0,
    "avg_loss": 0.0,
    "periods": 300,
}


# ---------------------------------------------------------------------------
# FailureAnalysis tests
# ---------------------------------------------------------------------------

class TestFailureAnalysis:
    """Tests for the FailureAnalysis dataclass."""

    def test_creation(self):
        analysis = FailureAnalysis(
            failure_type="low_return",
            description="Strategy generated negative returns",
            severity=0.8,
            affected_metrics=["total_return", "sharpe_ratio"],
        )
        assert analysis.failure_type == "low_return"
        assert analysis.severity == 0.8
        assert "total_return" in analysis.affected_metrics

    def test_severity_range(self):
        """Severity should be between 0 and 1."""
        analysis = FailureAnalysis(
            failure_type="test",
            description="test",
            severity=0.5,
            affected_metrics=[],
        )
        assert 0 <= analysis.severity <= 1


# ---------------------------------------------------------------------------
# Proposal tests
# ---------------------------------------------------------------------------

class TestProposal:
    """Tests for the Proposal dataclass."""

    def test_creation(self):
        proposal = Proposal(
            mutation_type="parameter_tune",
            target="rsi_period",
            description="Increase RSI period for smoother signals",
            details={"param": "rsi_period", "old": 14, "new": 20},
            confidence=0.7,
        )
        assert proposal.mutation_type == "parameter_tune"
        assert proposal.target == "rsi_period"
        assert proposal.confidence == 0.7

    def test_confidence_range(self):
        """Confidence should be between 0 and 1."""
        proposal = Proposal(
            mutation_type="test",
            target="test",
            description="test",
            details={},
            confidence=0.5,
        )
        assert 0 <= proposal.confidence <= 1


# ---------------------------------------------------------------------------
# Proposer tests
# ---------------------------------------------------------------------------

class TestProposer:
    """Tests for the Proposer class."""

    def test_analyze_low_return(self):
        """Should identify low return as a failure."""
        proposer = Proposer()
        analyses = proposer.analyze(STRATEGY_YAML, LOW_RETURN_FEEDBACK)
        assert len(analyses) > 0
        types = [a.failure_type for a in analyses]
        assert "low_return" in types or "negative_return" in types

    def test_analyze_high_drawdown(self):
        """Should identify excessive drawdown."""
        proposer = Proposer()
        analyses = proposer.analyze(STRATEGY_YAML, HIGH_DRAWDOWN_FEEDBACK)
        assert len(analyses) > 0
        types = [a.failure_type for a in analyses]
        assert any("drawdown" in t for t in types)

    def test_analyze_no_trades(self):
        """Should identify lack of trades as a failure."""
        proposer = Proposer()
        analyses = proposer.analyze(STRATEGY_YAML, FEW_TRADES_FEEDBACK)
        assert len(analyses) > 0
        types = [a.failure_type for a in analyses]
        assert any("trade" in t.lower() or "few" in t.lower() or "no_trades" in t.lower() for t in types)

    def test_propose_returns_proposals(self):
        """Should produce at least one proposal for a failure analysis."""
        proposer = Proposer()
        analyses = proposer.analyze(STRATEGY_YAML, LOW_RETURN_FEEDBACK)
        proposals = proposer.propose(STRATEGY_YAML, analyses)
        assert len(proposals) > 0
        assert all(isinstance(p, Proposal) for p in proposals)

    def test_proposals_have_valid_mutation_types(self):
        """Proposals should have recognized mutation types."""
        valid_types = {"parameter_tune", "indicator_swap", "add_filter", "remove_filter",
                       "adjust_risk", "combine_strategy", "change_entry", "change_exit"}
        proposer = Proposer()
        analyses = proposer.analyze(STRATEGY_YAML, HIGH_DRAWDOWN_FEEDBACK)
        proposals = proposer.propose(STRATEGY_YAML, analyses)
        for p in proposals:
            assert p.mutation_type in valid_types, f"Unknown type: {p.mutation_type}"

    def test_drawdown_proposals_address_risk(self):
        """Proposals for high drawdown should include risk adjustments."""
        proposer = Proposer()
        analyses = proposer.analyze(STRATEGY_YAML, HIGH_DRAWDOWN_FEEDBACK)
        proposals = proposer.propose(STRATEGY_YAML, analyses)
        types = [p.mutation_type for p in proposals]
        assert "adjust_risk" in types or "add_filter" in types

    def test_no_trades_proposals_relax_entry(self):
        """When no trades occur, proposals should relax entry conditions."""
        proposer = Proposer()
        analyses = proposer.analyze(STRATEGY_YAML, FEW_TRADES_FEEDBACK)
        proposals = proposer.propose(STRATEGY_YAML, analyses)
        # Should suggest loosening entry criteria
        assert any("entry" in p.target.lower() or "parameter" in p.mutation_type
                    for p in proposals)

    def test_empty_feedback_no_crash(self):
        """Empty or minimal feedback should not crash."""
        proposer = Proposer()
        analyses = proposer.analyze(STRATEGY_YAML, {"score": {}, "trade_count": 0})
        assert isinstance(analyses, list)
