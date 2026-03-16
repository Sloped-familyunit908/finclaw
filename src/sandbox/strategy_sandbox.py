"""
FinClaw - Strategy Sandbox
Safe environment for testing user-defined strategies with restricted execution.
"""

from __future__ import annotations

import ast
import math
from dataclasses import dataclass, field
from typing import Any


# Whitelist of safe builtins
_SAFE_BUILTINS = {
    "abs": abs, "min": min, "max": max, "sum": sum,
    "len": len, "range": range, "enumerate": enumerate, "zip": zip,
    "int": int, "float": float, "str": str, "bool": bool,
    "list": list, "dict": dict, "tuple": tuple, "set": set,
    "sorted": sorted, "reversed": reversed, "round": round,
    "True": True, "False": False, "None": None,
    "print": lambda *a, **kw: None,  # silenced
}

# Forbidden AST node types
_FORBIDDEN_NODES = {
    ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal,
    ast.AsyncFunctionDef, ast.AsyncFor, ast.AsyncWith, ast.Await,
}

# Forbidden attribute names
_FORBIDDEN_ATTRS = {
    "__import__", "__builtins__", "__subclasses__", "__class__",
    "__bases__", "__globals__", "__code__", "eval", "exec",
    "compile", "open", "input", "__dict__",
}


@dataclass
class BacktestResult:
    """Result of a sandbox backtest."""
    total_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    num_trades: int = 0
    win_rate: float = 0.0
    signals: list[dict[str, Any]] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class StrategySandbox:
    """
    Safe sandbox for running user strategy code.
    
    Validates code safety, compiles in restricted namespace,
    and runs backtests against provided data.
    """

    def __init__(self, strategy_code: str):
        self.strategy_code = strategy_code
        self._compiled = None
        self._namespace: dict[str, Any] = {}
        self._warnings: list[str] = []

    def validate(self) -> list[str]:
        """
        Validate strategy code for safety and correctness.
        Returns list of warnings/errors. Empty = OK.
        """
        warnings: list[str] = []

        # Parse AST
        try:
            tree = ast.parse(self.strategy_code)
        except SyntaxError as e:
            return [f"Syntax error: {e}"]

        # Check for forbidden nodes
        for node in ast.walk(tree):
            if type(node) in _FORBIDDEN_NODES:
                warnings.append(f"Forbidden construct: {type(node).__name__} at line {getattr(node, 'lineno', '?')}")

            # Check attribute access
            if isinstance(node, ast.Attribute):
                if node.attr in _FORBIDDEN_ATTRS:
                    warnings.append(f"Forbidden attribute: {node.attr} at line {node.lineno}")

            # Check function calls to dangerous builtins
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in ("eval", "exec", "compile", "open", "__import__"):
                    warnings.append(f"Forbidden call: {node.func.id} at line {node.lineno}")

        # Check for generate_signals function
        has_generate = any(
            isinstance(node, ast.FunctionDef) and node.name == "generate_signals"
            for node in ast.walk(tree)
        )
        if not has_generate:
            warnings.append("Missing required function: generate_signals(data)")

        self._warnings = warnings
        return warnings

    def compile(self) -> bool:
        """Compile and execute code in restricted namespace. Returns True on success."""
        warnings = self.validate()
        errors = [w for w in warnings if "Forbidden" in w or "Syntax" in w]
        if errors:
            return False

        namespace = {"__builtins__": _SAFE_BUILTINS, "math": math}
        try:
            code = builtins_compile(self.strategy_code, "<strategy>", "exec")
            exec(code, namespace)
        except Exception as e:
            self._warnings.append(f"Execution error: {e}")
            return False

        self._namespace = namespace
        self._compiled = True
        return True

    def backtest(self, data: list[dict[str, Any]]) -> BacktestResult:
        """
        Run the strategy against historical data.
        
        data: list of dicts with at minimum 'date', 'close', 'ticker' keys.
        The strategy's generate_signals(data_point) should return a list of
        signal dicts with 'side' and optionally 'quantity', 'ticker'.
        """
        result = BacktestResult()

        if not self._compiled:
            if not self.compile():
                result.errors = list(self._warnings)
                return result

        gen_signals = self._namespace.get("generate_signals")
        if not callable(gen_signals):
            result.errors.append("generate_signals is not callable")
            return result

        # Simple backtest loop
        capital = 100000.0
        cash = capital
        position = 0.0
        entry_price = 0.0
        equity_curve = [capital]
        trades = 0
        wins = 0

        for point in data:
            price = point.get("close", point.get("price", 0))
            if price <= 0:
                equity_curve.append(equity_curve[-1])
                continue

            try:
                signals = gen_signals(point)
            except Exception as e:
                result.errors.append(f"Signal error at {point.get('date', '?')}: {e}")
                signals = []

            if not isinstance(signals, list):
                signals = [signals] if isinstance(signals, dict) else []

            for sig in signals:
                side = sig.get("side", "")
                qty = sig.get("quantity", 100)

                if side == "buy" and position <= 0 and cash >= qty * price:
                    if position < 0:
                        # Close short
                        pnl = (entry_price - price) * abs(position)
                        cash += pnl + abs(position) * price
                        if pnl > 0:
                            wins += 1
                        trades += 1
                        position = 0

                    cost = qty * price
                    if cost <= cash:
                        cash -= cost
                        position = qty
                        entry_price = price
                        result.signals.append({"side": "buy", "price": price, "date": point.get("date")})

                elif side == "sell" and position > 0:
                    proceeds = position * price
                    pnl = (price - entry_price) * position
                    cash += proceeds
                    if pnl > 0:
                        wins += 1
                    trades += 1
                    position = 0
                    result.signals.append({"side": "sell", "price": price, "date": point.get("date")})

            # Mark to market
            mtm = cash + position * price if position > 0 else cash
            equity_curve.append(mtm)

        # Close any open position at last price
        if position != 0 and data:
            last_price = data[-1].get("close", data[-1].get("price", 0))
            if position > 0:
                cash += position * last_price
                pnl = (last_price - entry_price) * position
                if pnl > 0:
                    wins += 1
                trades += 1

        result.equity_curve = equity_curve
        result.num_trades = trades
        result.total_return = (equity_curve[-1] / capital - 1) if capital > 0 else 0
        result.win_rate = wins / trades if trades > 0 else 0

        # Max drawdown
        peak = equity_curve[0]
        max_dd = 0.0
        for v in equity_curve:
            if v > peak:
                peak = v
            dd = (peak - v) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        result.max_drawdown = max_dd

        # Sharpe
        if len(equity_curve) > 2:
            returns = [(equity_curve[i] / equity_curve[i-1]) - 1 for i in range(1, len(equity_curve)) if equity_curve[i-1] > 0]
            if returns:
                avg = sum(returns) / len(returns)
                std = (sum((r - avg)**2 for r in returns) / max(len(returns)-1, 1)) ** 0.5
                result.sharpe_ratio = (avg / std * math.sqrt(252)) if std > 0 else 0

        return result


# Use real compile under a different name to avoid shadowing
builtins_compile = compile
