"""
Strategy DSL — parse YAML strategy definitions into executable Strategy objects.

Example YAML:
    name: Golden Cross
    universe: sp500
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

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import yaml

from .expression import ExpressionEvaluator, OHLCVData


@dataclass
class RiskConfig:
    """Risk management parameters."""
    stop_loss: float | None = None       # as fraction, e.g. 0.05
    take_profit: float | None = None
    max_position: float | None = None    # max fraction per position
    max_drawdown: float | None = None
    trailing_stop: float | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> "RiskConfig":
        if not d:
            return cls()
        return cls(
            stop_loss=_parse_pct(d.get("stop_loss")),
            take_profit=_parse_pct(d.get("take_profit")),
            max_position=_parse_pct(d.get("max_position")),
            max_drawdown=_parse_pct(d.get("max_drawdown")),
            trailing_stop=_parse_pct(d.get("trailing_stop")),
        )


@dataclass
class Strategy:
    """Parsed strategy ready for execution."""
    name: str
    description: str = ""
    universe: str = ""
    entry_conditions: list[str] = field(default_factory=list)
    exit_conditions: list[str] = field(default_factory=list)
    exit_or_conditions: list[str] = field(default_factory=list)
    risk: RiskConfig = field(default_factory=RiskConfig)
    rebalance: str = "daily"
    params: dict[str, Any] = field(default_factory=dict)

    def should_enter(self, data: OHLCVData, index: int = -1) -> bool:
        """Check if all entry conditions are met at given bar."""
        evaluator = ExpressionEvaluator()
        return all(evaluator.evaluate(cond, data, index) for cond in self.entry_conditions)

    def should_exit(self, data: OHLCVData, index: int = -1) -> bool:
        """Check if exit conditions are met (AND conditions all true, OR any true)."""
        evaluator = ExpressionEvaluator()
        # AND conditions — all must be true
        and_met = all(evaluator.evaluate(c, data, index) for c in self.exit_conditions) if self.exit_conditions else False
        # OR conditions — any triggers exit
        or_met = any(evaluator.evaluate(c, data, index) for c in self.exit_or_conditions) if self.exit_or_conditions else False
        return and_met or or_met

    def to_yaml(self) -> str:
        """Serialize back to YAML."""
        d: dict[str, Any] = {"name": self.name}
        if self.description:
            d["description"] = self.description
        if self.universe:
            d["universe"] = self.universe
        if self.entry_conditions:
            d["entry"] = list(self.entry_conditions)
        exit_list: list[Any] = list(self.exit_conditions)
        for cond in self.exit_or_conditions:
            exit_list.append({"OR": cond})
        if exit_list:
            d["exit"] = exit_list
        risk_d = {}
        if self.risk.stop_loss is not None:
            risk_d["stop_loss"] = f"{self.risk.stop_loss * 100:.0f}%"
        if self.risk.take_profit is not None:
            risk_d["take_profit"] = f"{self.risk.take_profit * 100:.0f}%"
        if self.risk.max_position is not None:
            risk_d["max_position"] = f"{self.risk.max_position * 100:.0f}%"
        if self.risk.max_drawdown is not None:
            risk_d["max_drawdown"] = f"{self.risk.max_drawdown * 100:.0f}%"
        if self.risk.trailing_stop is not None:
            risk_d["trailing_stop"] = f"{self.risk.trailing_stop * 100:.0f}%"
        if risk_d:
            d["risk"] = risk_d
        if self.rebalance != "daily":
            d["rebalance"] = self.rebalance
        if self.params:
            d["params"] = dict(self.params)
        return yaml.dump(d, default_flow_style=False, sort_keys=False)


class StrategyDSL:
    """Parse YAML strategy definitions into executable Strategy objects."""

    def parse(self, yaml_str: str) -> Strategy:
        """Parse a YAML string into a Strategy."""
        config = yaml.safe_load(yaml_str)
        if not isinstance(config, dict):
            raise ValueError("Strategy YAML must be a mapping")
        errors = self.validate(config)
        if errors:
            raise ValueError(f"Strategy validation failed: {'; '.join(errors)}")
        return self._build(config)

    def parse_file(self, path: str) -> Strategy:
        """Parse a YAML file into a Strategy."""
        with open(path, "r", encoding="utf-8") as f:
            return self.parse(f.read())

    def validate(self, config: dict[str, Any]) -> list[str]:
        """Validate strategy config dict, return list of error messages."""
        errors: list[str] = []
        if "name" not in config:
            errors.append("Missing required field: 'name'")
        if "entry" not in config:
            errors.append("Missing required field: 'entry'")
        if not isinstance(config.get("entry", []), list):
            errors.append("'entry' must be a list of expressions")
        if "exit" in config and not isinstance(config["exit"], list):
            errors.append("'exit' must be a list of expressions")

        # Validate expressions are parseable
        evaluator = ExpressionEvaluator()
        for expr in config.get("entry", []):
            if isinstance(expr, str):
                try:
                    import ast as _ast
                    _ast.parse(expr, mode="eval")
                except SyntaxError as e:
                    errors.append(f"Invalid entry expression '{expr}': {e}")
        for item in config.get("exit", []):
            expr = item
            if isinstance(item, dict):
                expr = item.get("OR", item.get("or", ""))
            if isinstance(expr, str) and expr:
                try:
                    import ast as _ast
                    _ast.parse(expr, mode="eval")
                except SyntaxError as e:
                    errors.append(f"Invalid exit expression '{expr}': {e}")

        # Validate risk percentages
        risk = config.get("risk", {})
        if isinstance(risk, dict):
            for key in ("stop_loss", "take_profit", "max_position", "max_drawdown", "trailing_stop"):
                val = risk.get(key)
                if val is not None:
                    parsed = _parse_pct(val)
                    if parsed is None:
                        errors.append(f"Invalid risk value for '{key}': {val}")
                    elif parsed < 0 or parsed > 1:
                        errors.append(f"Risk '{key}' must be between 0% and 100%: {val}")

        # Validate rebalance
        valid_rebalance = {"daily", "weekly", "monthly", "quarterly", "yearly"}
        rebal = config.get("rebalance", "daily")
        if isinstance(rebal, str) and rebal.lower() not in valid_rebalance:
            errors.append(f"Invalid rebalance frequency: '{rebal}' (valid: {', '.join(sorted(valid_rebalance))})")

        return errors

    def _build(self, config: dict[str, Any]) -> Strategy:
        entry_conds = [e for e in config.get("entry", []) if isinstance(e, str)]
        exit_and: list[str] = []
        exit_or: list[str] = []
        for item in config.get("exit", []):
            if isinstance(item, str):
                exit_and.append(item)
            elif isinstance(item, dict):
                or_expr = item.get("OR") or item.get("or")
                if or_expr:
                    exit_or.append(or_expr)

        return Strategy(
            name=config["name"],
            description=config.get("description", ""),
            universe=config.get("universe", ""),
            entry_conditions=entry_conds,
            exit_conditions=exit_and,
            exit_or_conditions=exit_or,
            risk=RiskConfig.from_dict(config.get("risk")),
            rebalance=config.get("rebalance", "daily"),
            params=config.get("params", {}),
        )


def _parse_pct(val: Any) -> float | None:
    """Parse percentage: '5%' → 0.05, 0.05 → 0.05, 5 → 0.05."""
    if val is None:
        return None
    if isinstance(val, str):
        val = val.strip()
        m = re.match(r"^([\d.]+)\s*%$", val)
        if m:
            return float(m.group(1)) / 100.0
        try:
            v = float(val)
            return v / 100.0 if v > 1 else v
        except ValueError:
            return None
    if isinstance(val, (int, float)):
        return val / 100.0 if val > 1 else float(val)
    return None
