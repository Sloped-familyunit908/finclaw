"""
Mutator — apply targeted mutations to YAML strategy configs.

Takes a strategy YAML string and a :class:`Proposal`, returns a new
mutated YAML string.  Supports parameter tuning, indicator swapping,
filter add/remove, risk adjustment, and strategy combination.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

import yaml

from .proposer import Proposal


class MutationType(str, Enum):
    """Supported mutation types."""

    PARAMETER_TUNE = "parameter_tune"
    INDICATOR_SWAP = "indicator_swap"
    ADD_FILTER = "add_filter"
    REMOVE_FILTER = "remove_filter"
    ADJUST_RISK = "adjust_risk"
    COMBINE_STRATEGY = "combine_strategy"


class Mutator:
    """Apply targeted mutations to YAML strategy configs."""

    def mutate(
        self,
        strategy_yaml: str,
        proposal: Proposal,
        *,
        feedback: dict[str, Any] | None = None,
    ) -> str:
        """Apply *proposal* to *strategy_yaml* and return the mutated YAML.

        Parameters
        ----------
        strategy_yaml:
            The source strategy as a YAML string.
        proposal:
            The mutation to apply.
        feedback:
            Optional evaluation feedback (unused today, reserved for
            context-aware mutations).

        Returns
        -------
        str
            Mutated strategy as a YAML string.
        """
        config = yaml.safe_load(strategy_yaml)
        if not isinstance(config, dict):
            raise ValueError("strategy_yaml must parse to a dict")

        handlers = {
            "parameter_tune": self._parameter_tune,
            "indicator_swap": self._indicator_swap,
            "add_filter": self._add_filter,
            "remove_filter": self._remove_filter,
            "adjust_risk": self._adjust_risk,
            "combine_strategy": self._combine_strategy,
            "change_entry": self._change_entry,
            "change_exit": self._change_exit,
        }
        handler = handlers.get(proposal.mutation_type)
        if handler is None:
            raise ValueError(f"Unknown mutation type: {proposal.mutation_type}")

        # We work on the raw YAML string for textual replacements,
        # but on the parsed dict for structural changes.
        mutated_yaml = strategy_yaml
        mutated_config = config

        if proposal.mutation_type in ("parameter_tune", "indicator_swap"):
            mutated_yaml = handler(strategy_yaml, proposal)
            return mutated_yaml
        else:
            handler(mutated_config, proposal)
            return yaml.dump(mutated_config, default_flow_style=False, sort_keys=False)

    # ------------------------------------------------------------------
    # Mutation handlers
    # ------------------------------------------------------------------

    @staticmethod
    def _parameter_tune(yaml_str: str, proposal: Proposal) -> str:
        """Replace indicator(old_param) with indicator(new_param)."""
        details = proposal.details
        indicator = details.get("indicator", "")
        old_param = details.get("old_param")
        new_param = details.get("new_param")
        if indicator and old_param is not None and new_param is not None:
            old_call = f"{indicator}({old_param})"
            new_call = f"{indicator}({new_param})"
            return yaml_str.replace(old_call, new_call)
        return yaml_str

    @staticmethod
    def _indicator_swap(yaml_str: str, proposal: Proposal) -> str:
        """Replace old_indicator(N) with new_indicator(N) everywhere."""
        details = proposal.details
        old_ind = details.get("old_indicator", "")
        new_ind = details.get("new_indicator", "")
        if old_ind and new_ind:
            # Replace indicator name but keep the parameter
            pattern = re.compile(rf'\b{re.escape(old_ind)}\(')
            return pattern.sub(f"{new_ind}(", yaml_str)
        return yaml_str

    @staticmethod
    def _add_filter(config: dict, proposal: Proposal) -> None:
        """Add a filter condition to entry or exit."""
        target = proposal.target.lower()
        new_filter = proposal.details.get("filter", "")
        if not new_filter:
            return

        section = "entry" if "entry" in target else "exit"
        if section not in config:
            config[section] = []
        config[section].append(new_filter)

    @staticmethod
    def _remove_filter(config: dict, proposal: Proposal) -> None:
        """Remove conditions matching a pattern from entry or exit."""
        target = proposal.target.lower()
        pattern = proposal.details.get("filter_pattern", "")
        if not pattern:
            return

        section = "entry" if "entry" in target else "exit"
        if section not in config:
            return

        original = config[section]
        config[section] = [
            c for c in original
            if not (isinstance(c, str) and pattern.lower() in c.lower())
        ]

    @staticmethod
    def _adjust_risk(config: dict, proposal: Proposal) -> None:
        """Update risk parameters."""
        if "risk" not in config:
            config["risk"] = {}

        for key in ("stop_loss", "take_profit", "max_position", "max_drawdown", "trailing_stop"):
            if key in proposal.details:
                config["risk"][key] = proposal.details[key]

    @staticmethod
    def _combine_strategy(config: dict, proposal: Proposal) -> None:
        """Merge conditions from another strategy into this one."""
        other_yaml = proposal.details.get("other_strategy", "")
        if not other_yaml:
            return

        other = yaml.safe_load(other_yaml)
        if not isinstance(other, dict):
            return

        # Merge entry conditions (union)
        existing_entry = set(str(c) for c in config.get("entry", []))
        for cond in other.get("entry", []):
            if str(cond) not in existing_entry:
                config.setdefault("entry", []).append(cond)
                existing_entry.add(str(cond))

        # Merge exit OR conditions
        existing_exit = set(str(c) for c in config.get("exit", []))
        for cond in other.get("exit", []):
            cond_str = str(cond)
            if cond_str not in existing_exit:
                config.setdefault("exit", []).append(cond)
                existing_exit.add(cond_str)

        # Update name to indicate combination
        config["name"] = f"{config.get('name', 'Strategy')} + {other.get('name', 'Other')}"

    @staticmethod
    def _change_entry(config: dict, proposal: Proposal) -> None:
        """Replace entry conditions."""
        new_conditions = proposal.details.get("conditions", [])
        if new_conditions:
            config["entry"] = new_conditions

    @staticmethod
    def _change_exit(config: dict, proposal: Proposal) -> None:
        """Replace exit conditions."""
        new_conditions = proposal.details.get("conditions", [])
        if new_conditions:
            config["exit"] = new_conditions
