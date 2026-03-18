"""
Proposer — analyze backtest failures and propose targeted improvements.

Examines evaluation feedback to identify *why* a strategy underperformed,
then generates concrete :class:`Proposal` objects for the :class:`Mutator`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class FailureAnalysis:
    """Diagnosis of a single failure mode."""

    failure_type: str          # e.g. "low_return", "high_drawdown", "no_trades"
    description: str
    severity: float            # 0–1
    affected_metrics: list[str] = field(default_factory=list)


@dataclass
class Proposal:
    """A concrete mutation proposal to improve a strategy."""

    mutation_type: str         # one of the valid types
    target: str                # what part of the strategy to change
    description: str
    details: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5   # 0–1

    # Valid mutation types
    VALID_TYPES = frozenset({
        "parameter_tune", "indicator_swap", "add_filter", "remove_filter",
        "adjust_risk", "combine_strategy", "change_entry", "change_exit",
    })


# ---------------------------------------------------------------------------
# Proposer
# ---------------------------------------------------------------------------

class Proposer:
    """Analyze strategy feedback and produce improvement proposals."""

    # Thresholds for failure detection
    _SHARPE_THRESHOLD = 0.5
    _RETURN_THRESHOLD = 0.0
    _DRAWDOWN_THRESHOLD = -0.20
    _WINRATE_THRESHOLD = 0.45
    _MIN_TRADES = 3

    def analyze(self, strategy_yaml: str, feedback: dict[str, Any]) -> list[FailureAnalysis]:
        """Identify failure modes in the backtest results."""
        analyses: list[FailureAnalysis] = []
        score = feedback.get("score", {})
        trade_count = feedback.get("trade_count", score.get("total_trades", 0))

        # ---- No / very few trades ----
        if trade_count < self._MIN_TRADES:
            analyses.append(FailureAnalysis(
                failure_type="no_trades",
                description=f"Strategy generated only {trade_count} trades — entry conditions may be too restrictive",
                severity=0.9,
                affected_metrics=["total_trades", "total_return"],
            ))

        # ---- Negative / low return ----
        total_return = score.get("total_return", 0.0)
        if total_return < self._RETURN_THRESHOLD:
            analyses.append(FailureAnalysis(
                failure_type="low_return",
                description=f"Negative total return ({total_return:.2%})",
                severity=min(abs(total_return) * 2, 1.0),
                affected_metrics=["total_return", "sharpe_ratio"],
            ))
        elif total_return < 0.05 and trade_count >= self._MIN_TRADES:
            analyses.append(FailureAnalysis(
                failure_type="low_return",
                description=f"Very low total return ({total_return:.2%})",
                severity=0.5,
                affected_metrics=["total_return"],
            ))

        # ---- High drawdown ----
        max_dd = score.get("max_drawdown", 0.0)
        if max_dd < self._DRAWDOWN_THRESHOLD:
            analyses.append(FailureAnalysis(
                failure_type="high_drawdown",
                description=f"Excessive drawdown ({max_dd:.2%})",
                severity=min(abs(max_dd) * 2, 1.0),
                affected_metrics=["max_drawdown", "sharpe_ratio"],
            ))

        # ---- Low Sharpe ----
        sharpe = score.get("sharpe_ratio", 0.0)
        if sharpe < self._SHARPE_THRESHOLD and trade_count >= self._MIN_TRADES:
            analyses.append(FailureAnalysis(
                failure_type="low_sharpe",
                description=f"Low Sharpe ratio ({sharpe:.2f})",
                severity=0.6,
                affected_metrics=["sharpe_ratio"],
            ))

        # ---- Low win rate ----
        win_rate = score.get("win_rate", 0.0)
        if win_rate < self._WINRATE_THRESHOLD and trade_count >= self._MIN_TRADES:
            analyses.append(FailureAnalysis(
                failure_type="low_win_rate",
                description=f"Low win rate ({win_rate:.2%})",
                severity=0.5,
                affected_metrics=["win_rate"],
            ))

        # ---- Poor risk/reward ----
        avg_win = feedback.get("avg_win", 0.0)
        avg_loss = abs(feedback.get("avg_loss", 0.0))
        if avg_loss > 0 and avg_win > 0 and avg_win / avg_loss < 1.0 and trade_count >= self._MIN_TRADES:
            analyses.append(FailureAnalysis(
                failure_type="poor_risk_reward",
                description=f"Avg win ({avg_win:.2%}) smaller than avg loss ({avg_loss:.2%})",
                severity=0.6,
                affected_metrics=["win_rate", "total_return"],
            ))

        return analyses

    def propose(self, strategy_yaml: str, analyses: list[FailureAnalysis]) -> list[Proposal]:
        """Generate improvement proposals based on failure analyses."""
        proposals: list[Proposal] = []
        config = yaml.safe_load(strategy_yaml) or {}

        for analysis in analyses:
            proposals.extend(self._proposals_for(analysis, config))

        return proposals

    # ------------------------------------------------------------------
    # Internal: generate proposals per failure type
    # ------------------------------------------------------------------

    def _proposals_for(self, analysis: FailureAnalysis, config: dict) -> list[Proposal]:
        handlers = {
            "no_trades": self._propose_for_no_trades,
            "low_return": self._propose_for_low_return,
            "high_drawdown": self._propose_for_high_drawdown,
            "low_sharpe": self._propose_for_low_sharpe,
            "low_win_rate": self._propose_for_low_win_rate,
            "poor_risk_reward": self._propose_for_poor_risk_reward,
        }
        handler = handlers.get(analysis.failure_type, self._propose_generic)
        return handler(analysis, config)

    def _propose_for_no_trades(self, analysis: FailureAnalysis, config: dict) -> list[Proposal]:
        """Too few trades → relax entry conditions or adjust parameters."""
        proposals: list[Proposal] = []
        entry = config.get("entry", [])

        # Suggest removing the most restrictive filter
        if len(entry) > 1:
            proposals.append(Proposal(
                mutation_type="remove_filter",
                target="entry",
                description="Remove most restrictive entry filter to generate more signals",
                details={"filter_pattern": self._guess_restrictive_filter(entry)},
                confidence=0.7,
            ))

        # Suggest widening indicator parameters
        params = self._extract_indicator_params(entry)
        if params:
            indicator, period = params[0]  # just the first one
            proposals.append(Proposal(
                mutation_type="parameter_tune",
                target=f"entry_{indicator}",
                description=f"Widen {indicator} period ({period} → {max(period - 5, 5)}) for more signals",
                details={"indicator": indicator, "old_param": period, "new_param": max(period - 5, 5)},
                confidence=0.6,
            ))

        return proposals

    def _propose_for_low_return(self, analysis: FailureAnalysis, config: dict) -> list[Proposal]:
        proposals: list[Proposal] = []

        # Suggest indicator swap for better trend detection
        entry = config.get("entry", [])
        for cond in entry:
            if isinstance(cond, str) and "sma(" in cond:
                proposals.append(Proposal(
                    mutation_type="indicator_swap",
                    target="entry",
                    description="Swap SMA for EMA to capture trends faster",
                    details={"old_indicator": "sma", "new_indicator": "ema"},
                    confidence=0.6,
                ))
                break

        # Suggest loosening take profit
        risk = config.get("risk", {})
        if risk.get("take_profit"):
            proposals.append(Proposal(
                mutation_type="adjust_risk",
                target="risk",
                description="Increase take profit to let winners run",
                details={"take_profit": self._increase_pct(risk["take_profit"])},
                confidence=0.5,
            ))

        return proposals

    def _propose_for_high_drawdown(self, analysis: FailureAnalysis, config: dict) -> list[Proposal]:
        proposals: list[Proposal] = []

        # Tighten stop loss
        risk = config.get("risk", {})
        proposals.append(Proposal(
            mutation_type="adjust_risk",
            target="risk",
            description="Tighten stop loss to limit drawdown",
            details={"stop_loss": self._decrease_pct(risk.get("stop_loss", "5%"))},
            confidence=0.8,
        ))

        # Add volatility filter
        proposals.append(Proposal(
            mutation_type="add_filter",
            target="entry",
            description="Add ADX filter to avoid choppy markets",
            details={"filter": "adx(14) > 25"},
            confidence=0.6,
        ))

        return proposals

    def _propose_for_low_sharpe(self, analysis: FailureAnalysis, config: dict) -> list[Proposal]:
        proposals: list[Proposal] = []

        # Suggest parameter tuning on indicators
        entry = config.get("entry", [])
        params = self._extract_indicator_params(entry)
        for indicator, period in params:
            new_period = int(period * 1.3)  # slow down for smoother signals
            proposals.append(Proposal(
                mutation_type="parameter_tune",
                target=f"entry_{indicator}",
                description=f"Increase {indicator} period for smoother signals ({period} → {new_period})",
                details={"indicator": indicator, "old_param": period, "new_param": new_period},
                confidence=0.5,
            ))

        return proposals

    def _propose_for_low_win_rate(self, analysis: FailureAnalysis, config: dict) -> list[Proposal]:
        proposals: list[Proposal] = []

        # Add confirmation filter
        proposals.append(Proposal(
            mutation_type="add_filter",
            target="entry",
            description="Add volume confirmation to reduce false signals",
            details={"filter": "volume > sma_volume(20) * 1.5"},
            confidence=0.6,
        ))

        return proposals

    def _propose_for_poor_risk_reward(self, analysis: FailureAnalysis, config: dict) -> list[Proposal]:
        proposals: list[Proposal] = []
        risk = config.get("risk", {})

        proposals.append(Proposal(
            mutation_type="adjust_risk",
            target="risk",
            description="Widen take profit and tighten stop loss for better risk/reward",
            details={
                "stop_loss": self._decrease_pct(risk.get("stop_loss", "5%")),
                "take_profit": self._increase_pct(risk.get("take_profit", "15%")),
            },
            confidence=0.7,
        ))

        return proposals

    def _propose_generic(self, analysis: FailureAnalysis, config: dict) -> list[Proposal]:
        return [Proposal(
            mutation_type="parameter_tune",
            target="strategy",
            description=f"General improvement for: {analysis.description}",
            details={},
            confidence=0.3,
        )]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_indicator_params(conditions: list) -> list[tuple[str, int]]:
        """Extract (indicator, period) pairs from condition strings."""
        results: list[tuple[str, int]] = []
        pattern = re.compile(r'(sma|ema|rsi|macd|bb_upper|bb_lower|bb_middle|atr|adx|stochastic_k|stochastic_d|mfi)\((\d+)\)')
        for cond in conditions:
            if isinstance(cond, str):
                for match in pattern.finditer(cond):
                    results.append((match.group(1), int(match.group(2))))
        return results

    @staticmethod
    def _guess_restrictive_filter(conditions: list) -> str:
        """Guess which entry filter is most restrictive."""
        # Heuristic: volume and volatility filters are often most restrictive
        for cond in conditions:
            if isinstance(cond, str):
                if "volume" in cond.lower():
                    return "volume"
                if "adx" in cond.lower():
                    return "adx"
        # Fall back to last condition
        for cond in reversed(conditions):
            if isinstance(cond, str):
                # Extract first indicator name
                m = re.search(r'(sma|ema|rsi|macd|adx|volume)', cond)
                if m:
                    return m.group(1)
        return "filter"

    @staticmethod
    def _increase_pct(value: str | None) -> str:
        """Increase a percentage value (e.g. '10%' → '15%')."""
        if not value:
            return "15%"
        m = re.search(r'(\d+)', str(value))
        if m:
            return f"{int(m.group(1)) + 5}%"
        return "15%"

    @staticmethod
    def _decrease_pct(value: str | None) -> str:
        """Decrease a percentage value (e.g. '5%' → '3%')."""
        if not value:
            return "3%"
        m = re.search(r'(\d+)', str(value))
        if m:
            new_val = max(int(m.group(1)) - 2, 1)
            return f"{new_val}%"
        return "3%"
