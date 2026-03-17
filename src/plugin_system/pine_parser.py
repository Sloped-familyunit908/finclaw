"""
TradingView Pine Script Basic Parser for FinClaw
==================================================
Parses simple Pine Script strategies and converts them to FinClaw signals.

Supports a subset of Pine Script v5:
- indicator/strategy declarations
- Variable assignments
- ta.sma(), ta.ema(), ta.rsi(), ta.macd(), ta.crossover(), ta.crossunder()
- strategy.entry() / strategy.close()
- Simple if/else conditions
- close, open, high, low, volume built-ins

This is NOT a full Pine Script interpreter — it handles the 80% case
of simple indicator-based strategies shared on TradingView.

Usage::

    from src.plugin_system.pine_parser import PineScriptPlugin

    pine_code = '''
    //@version=5
    strategy("My SMA Cross", overlay=true)
    fast = ta.sma(close, 10)
    slow = ta.sma(close, 50)
    if ta.crossover(fast, slow)
        strategy.entry("Long", strategy.long)
    if ta.crossunder(fast, slow)
        strategy.close("Long")
    '''

    plugin = PineScriptPlugin(pine_code, name="pine_sma_cross")
    signals = plugin.generate_signals(df)
"""

from __future__ import annotations

import logging
import re
from typing import Any

import numpy as np
import pandas as pd

from src.plugin_system.plugin_types import StrategyPlugin

logger = logging.getLogger(__name__)


# ─── Pine Script built-in function implementations ──────────────

def _pine_sma(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(int(length)).mean()


def _pine_ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=int(length), adjust=False).mean()


def _pine_rsi(series: pd.Series, length: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / length, min_periods=int(length), adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, min_periods=int(length), adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _pine_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = _pine_ema(series, fast)
    ema_slow = _pine_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _pine_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


PINE_FUNCTIONS = {
    "ta.sma": _pine_sma,
    "ta.ema": _pine_ema,
    "ta.rsi": _pine_rsi,
}


# ─── Parser ─────────────────────────────────────────────────────

class PineParser:
    """
    Parses a subset of Pine Script and builds an execution plan.
    """

    def __init__(self, code: str):
        self.code = code
        self.lines = self._clean(code)
        self.variables: dict[str, Any] = {}
        self.entry_conditions: list[tuple[str, str]] = []  # (condition_expr, direction)
        self.close_conditions: list[str] = []
        self._parse()

    def _clean(self, code: str) -> list[str]:
        lines = []
        for line in code.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            # Remove inline comments
            if "//" in line:
                line = line[: line.index("//")].strip()
            lines.append(line)
        return lines

    def _parse(self) -> None:
        i = 0
        while i < len(self.lines):
            line = self.lines[i]

            # Skip version and indicator/strategy declarations
            if line.startswith("//@version") or line.startswith("indicator(") or line.startswith("strategy("):
                i += 1
                continue

            # Variable assignment: var = expr
            m = re.match(r"(\w+)\s*=\s*(.+)", line)
            if m and not line.startswith("if ") and "strategy." not in line:
                var_name, expr = m.group(1), m.group(2)
                self.variables[var_name] = expr
                i += 1
                continue

            # if condition with entry/close on next line
            if line.startswith("if "):
                condition = line[3:].strip()
                if i + 1 < len(self.lines):
                    action_line = self.lines[i + 1]
                    if "strategy.entry" in action_line:
                        direction = "long"
                        if "strategy.short" in action_line:
                            direction = "short"
                        self.entry_conditions.append((condition, direction))
                        i += 2
                        continue
                    elif "strategy.close" in action_line:
                        self.close_conditions.append(condition)
                        i += 2
                        continue

            # Inline strategy.entry
            if "strategy.entry" in line:
                # Try to extract condition from if prefix
                m2 = re.match(r"if\s+(.+)", line)
                if m2:
                    rest = m2.group(1)
                    # Split at strategy.entry
                    parts = rest.split("strategy.entry")
                    if len(parts) >= 1:
                        cond = parts[0].strip().rstrip(",").strip()
                        if cond:
                            direction = "long"
                            if "strategy.short" in line:
                                direction = "short"
                            self.entry_conditions.append((cond, direction))

            i += 1

    def execute(self, data: pd.DataFrame) -> pd.Series:
        """Execute the parsed Pine Script against OHLCV data."""
        env: dict[str, Any] = {
            "close": data["Close"],
            "open": data.get("Open", data["Close"]),
            "high": data.get("High", data["Close"]),
            "low": data.get("Low", data["Close"]),
            "volume": data.get("Volume", pd.Series(0, index=data.index)),
        }

        # Evaluate variable assignments
        for var_name, expr in self.variables.items():
            try:
                env[var_name] = self._eval_expr(expr, env)
            except Exception as exc:
                logger.debug("Failed to eval %s = %s: %s", var_name, expr, exc)

        # Generate signals
        signals = pd.Series(0, index=data.index)

        for condition, direction in self.entry_conditions:
            try:
                mask = self._eval_condition(condition, env)
                sig_val = 1 if direction == "long" else -1
                signals[mask] = sig_val
            except Exception as exc:
                logger.debug("Failed to eval entry condition %s: %s", condition, exc)

        for condition in self.close_conditions:
            try:
                mask = self._eval_condition(condition, env)
                signals[mask] = -1
            except Exception as exc:
                logger.debug("Failed to eval close condition %s: %s", condition, exc)

        return signals

    def _eval_expr(self, expr: str, env: dict) -> Any:
        """Evaluate a Pine Script expression."""
        expr = expr.strip()

        # ta.sma(source, length)
        m = re.match(r"ta\.sma\((.+?),\s*(\d+)\)", expr)
        if m:
            source = self._eval_expr(m.group(1), env)
            return _pine_sma(source, int(m.group(2)))

        # ta.ema(source, length)
        m = re.match(r"ta\.ema\((.+?),\s*(\d+)\)", expr)
        if m:
            source = self._eval_expr(m.group(1), env)
            return _pine_ema(source, int(m.group(2)))

        # ta.rsi(source, length)
        m = re.match(r"ta\.rsi\((.+?),\s*(\d+)\)", expr)
        if m:
            source = self._eval_expr(m.group(1), env)
            return _pine_rsi(source, int(m.group(2)))

        # ta.macd(source, fast, slow, signal) — returns tuple
        m = re.match(r"ta\.macd\((.+?),\s*(\d+),\s*(\d+),\s*(\d+)\)", expr)
        if m:
            source = self._eval_expr(m.group(1), env)
            return _pine_macd(source, int(m.group(2)), int(m.group(3)), int(m.group(4)))

        # Numeric literal
        try:
            return float(expr)
        except ValueError:
            pass

        # Variable reference
        if expr in env:
            return env[expr]

        # Arithmetic: simple a - b, a + b, a * b, a / b
        for op in [" - ", " + ", " * ", " / "]:
            if op in expr:
                parts = expr.split(op, 1)
                left = self._eval_expr(parts[0], env)
                right = self._eval_expr(parts[1], env)
                if op == " - ":
                    return left - right
                elif op == " + ":
                    return left + right
                elif op == " * ":
                    return left * right
                elif op == " / ":
                    return left / right

        raise ValueError(f"Cannot evaluate: {expr}")

    def _eval_condition(self, condition: str, env: dict) -> pd.Series:
        """Evaluate a Pine Script condition to a boolean Series."""
        condition = condition.strip()

        # ta.crossover(a, b)
        m = re.match(r"ta\.crossover\((.+?),\s*(.+?)\)", condition)
        if m:
            a = self._resolve(m.group(1), env)
            b = self._resolve(m.group(2), env)
            return (a.shift(1) <= b.shift(1)) & (a > b)

        # ta.crossunder(a, b)
        m = re.match(r"ta\.crossunder\((.+?),\s*(.+?)\)", condition)
        if m:
            a = self._resolve(m.group(1), env)
            b = self._resolve(m.group(2), env)
            return (a.shift(1) >= b.shift(1)) & (a < b)

        # Comparison operators
        for op, fn in [(" >= ", lambda a, b: a >= b),
                       (" <= ", lambda a, b: a <= b),
                       (" > ", lambda a, b: a > b),
                       (" < ", lambda a, b: a < b),
                       (" == ", lambda a, b: a == b)]:
            if op in condition:
                parts = condition.split(op, 1)
                a = self._resolve(parts[0].strip(), env)
                b = self._resolve(parts[1].strip(), env)
                return fn(a, b)

        # "and" / "or"
        if " and " in condition:
            parts = condition.split(" and ", 1)
            left = self._eval_condition(parts[0], env)
            right = self._eval_condition(parts[1], env)
            return left & right

        if " or " in condition:
            parts = condition.split(" or ", 1)
            left = self._eval_condition(parts[0], env)
            right = self._eval_condition(parts[1], env)
            return left | right

        raise ValueError(f"Cannot evaluate condition: {condition}")

    def _resolve(self, expr: str, env: dict) -> pd.Series:
        """Resolve an expression to a Series."""
        expr = expr.strip()
        try:
            val = float(expr)
            return pd.Series(val, index=env["close"].index)
        except (ValueError, TypeError):
            pass

        result = self._eval_expr(expr, env)
        if isinstance(result, pd.Series):
            return result
        return pd.Series(result, index=env["close"].index)


# ─── PineScriptPlugin ──────────────────────────────────────────


class PineScriptPlugin(StrategyPlugin):
    """
    FinClaw strategy plugin from TradingView Pine Script code.

    Parses simple Pine Script strategies and generates trading signals.
    Supports SMA, EMA, RSI, MACD, crossover/crossunder patterns.
    """

    version = "1.0.0"
    author = "Pine Script Adapter"

    def __init__(
        self,
        code: str,
        name: str = "pine_script",
        description: str | None = None,
        risk_level: str = "medium",
        markets: list[str] | None = None,
    ):
        self._code = code
        self.name = name
        self.risk_level = risk_level
        self.markets = markets or ["us_stock", "crypto"]

        self._parser = PineParser(code)

        # Try to extract strategy name from code
        m = re.search(r'strategy\("([^"]+)"', code)
        self.description = description or (m.group(1) if m else f"Pine Script: {name}")

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        return self._parser.execute(data)

    def get_parameters(self) -> dict[str, Any]:
        return {"variables": list(self._parser.variables.keys())}

    @property
    def source_code(self) -> str:
        """Return the original Pine Script source code."""
        return self._code


def from_pine(code: str, **kwargs: Any) -> PineScriptPlugin:
    """
    Convenience function to create a strategy from Pine Script.

    Example::

        plugin = from_pine('''
            //@version=5
            strategy("RSI Strategy")
            rsi = ta.rsi(close, 14)
            if rsi < 30
                strategy.entry("Long", strategy.long)
            if rsi > 70
                strategy.close("Long")
        ''', name="pine_rsi")
    """
    return PineScriptPlugin(code, **kwargs)
