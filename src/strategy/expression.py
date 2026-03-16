"""
Expression Evaluator — parse and evaluate strategy expressions like 'sma(20) > sma(50)'.

Supports: sma, ema, rsi, macd, macd_signal, macd_hist, bb_upper, bb_lower, bb_middle,
          atr, adx, volume, sma_volume, price, high, low, close, open, obv,
          stochastic_k, stochastic_d, mfi, cmf, sar
Plus arithmetic: +, -, *, /, and comparisons: >, <, >=, <=, ==, !=
"""

from __future__ import annotations

import ast
import operator
import re
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
from numpy.typing import NDArray

from src.ta import (
    sma as ta_sma,
    ema as ta_ema,
    rsi as ta_rsi,
    macd as ta_macd,
    bollinger_bands as ta_bb,
    atr as ta_atr,
    adx as ta_adx,
    obv as ta_obv,
    mfi as ta_mfi,
    cmf as ta_cmf,
    parabolic_sar as ta_sar,
    stochastic_rsi as ta_stoch_rsi,
)

Array = NDArray[np.float64]

# Comparison operators
_OPS = {
    ast.Gt: operator.gt,
    ast.Lt: operator.lt,
    ast.GtE: operator.ge,
    ast.LtE: operator.le,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
}

_ARITH = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


@dataclass
class OHLCVData:
    """Container for OHLCV data arrays."""
    open: Array
    high: Array
    low: Array
    close: Array
    volume: Array

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "OHLCVData":
        """Create from dict with keys: open, high, low, close, volume."""
        return cls(
            open=np.asarray(d["open"], dtype=np.float64),
            high=np.asarray(d["high"], dtype=np.float64),
            low=np.asarray(d["low"], dtype=np.float64),
            close=np.asarray(d["close"], dtype=np.float64),
            volume=np.asarray(d["volume"], dtype=np.float64),
        )

    @classmethod
    def from_dataframe(cls, df: Any) -> "OHLCVData":
        """Create from pandas DataFrame with columns Open/High/Low/Close/Volume."""
        cols = {c.lower(): c for c in df.columns}
        return cls(
            open=df[cols["open"]].values.astype(np.float64),
            high=df[cols["high"]].values.astype(np.float64),
            low=df[cols["low"]].values.astype(np.float64),
            close=df[cols["close"]].values.astype(np.float64),
            volume=df[cols["volume"]].values.astype(np.float64),
        )


class ExpressionEvaluator:
    """Evaluate strategy expressions against OHLCV data.

    Expressions like 'sma(20) > sma(50)' are parsed into an AST and
    evaluated to produce a boolean result for the latest bar.
    """

    def __init__(self) -> None:
        self._cache: dict[str, Array] = {}

    def evaluate(self, expr: str, data: OHLCVData, index: int = -1) -> bool:
        """Evaluate expression at given bar index (default: last bar).

        Returns True/False for comparison expressions, or the numeric value
        for pure numeric expressions.
        """
        self._data = data
        self._cache.clear()
        tree = ast.parse(expr.strip(), mode="eval")
        result = self._eval_node(tree.body, index)
        return bool(result)

    def evaluate_series(self, expr: str, data: OHLCVData) -> Array:
        """Evaluate expression across all bars, returning a boolean/numeric array."""
        self._data = data
        self._cache.clear()
        tree = ast.parse(expr.strip(), mode="eval")
        return self._eval_node_series(tree.body)

    # ── AST evaluation (single index) ──────────────────────────────

    def _eval_node(self, node: ast.AST, idx: int) -> Any:
        if isinstance(node, ast.Compare):
            left = self._eval_node(node.left, idx)
            for op_node, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator, idx)
                op_fn = _OPS.get(type(op_node))
                if op_fn is None:
                    raise ValueError(f"Unsupported comparison: {type(op_node).__name__}")
                if not op_fn(left, right):
                    return False
                left = right
            return True

        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left, idx)
            right = self._eval_node(node.right, idx)
            op_fn = _ARITH.get(type(node.op))
            if op_fn is None:
                raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
            return op_fn(left, right)

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -self._eval_node(node.operand, idx)

        if isinstance(node, ast.Call):
            series = self._resolve_function(node)
            return float(series[idx])

        if isinstance(node, ast.Constant):
            return float(node.value)

        if isinstance(node, ast.Name):
            series = self._resolve_name(node.id)
            return float(series[idx])

        raise ValueError(f"Unsupported expression node: {ast.dump(node)}")

    # ── AST evaluation (full series) ───────────────────────────────

    def _eval_node_series(self, node: ast.AST) -> Array:
        if isinstance(node, ast.Compare):
            left = self._eval_node_series(node.left)
            result = np.ones(len(left), dtype=bool)
            for op_node, comparator in zip(node.ops, node.comparators):
                right = self._eval_node_series(comparator)
                op_fn = _OPS.get(type(op_node))
                if op_fn is None:
                    raise ValueError(f"Unsupported comparison: {type(op_node).__name__}")
                result = result & op_fn(left, right)
                left = right
            return result

        if isinstance(node, ast.BinOp):
            left = self._eval_node_series(node.left)
            right = self._eval_node_series(node.right)
            op_fn = _ARITH.get(type(node.op))
            if op_fn is None:
                raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
            return op_fn(left, right)

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -self._eval_node_series(node.operand)

        if isinstance(node, ast.Call):
            return self._resolve_function(node)

        if isinstance(node, ast.Constant):
            n = len(self._data.close)
            return np.full(n, float(node.value))

        if isinstance(node, ast.Name):
            return self._resolve_name(node.id)

        raise ValueError(f"Unsupported expression node: {ast.dump(node)}")

    # ── Function / name resolution ─────────────────────────────────

    def _resolve_function(self, node: ast.Call) -> Array:
        if not isinstance(node.func, ast.Name):
            raise ValueError(f"Unsupported function call: {ast.dump(node)}")
        name = node.func.id
        args = [self._const_arg(a) for a in node.args]
        cache_key = f"{name}({','.join(str(a) for a in args)})"
        if cache_key in self._cache:
            return self._cache[cache_key]

        series = self._compute_indicator(name, args)
        self._cache[cache_key] = series
        return series

    def _resolve_name(self, name: str) -> Array:
        if name in self._cache:
            return self._cache[name]
        mapping = {
            "price": self._data.close,
            "close": self._data.close,
            "open": self._data.open,
            "high": self._data.high,
            "low": self._data.low,
            "volume": self._data.volume,
        }
        if name in mapping:
            return mapping[name]
        raise ValueError(f"Unknown variable: {name}")

    def _const_arg(self, node: ast.AST) -> float:
        if isinstance(node, ast.Constant):
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -self._const_arg(node.operand)
        raise ValueError(f"Function arguments must be constants, got: {ast.dump(node)}")

    def _compute_indicator(self, name: str, args: list[float]) -> Array:
        d = self._data
        if name == "sma":
            return ta_sma(d.close, int(args[0]))
        if name == "ema":
            return ta_ema(d.close, int(args[0]))
        if name == "rsi":
            return ta_rsi(d.close, int(args[0]) if args else 14)
        if name == "macd":
            line, _, _ = ta_macd(d.close, *(int(a) for a in args[:3]) if len(args) >= 3 else ())
            return line
        if name == "macd_signal":
            _, sig, _ = ta_macd(d.close, *(int(a) for a in args[:3]) if len(args) >= 3 else ())
            return sig
        if name == "macd_hist":
            _, _, hist = ta_macd(d.close, *(int(a) for a in args[:3]) if len(args) >= 3 else ())
            return hist
        if name == "bb_upper":
            return ta_bb(d.close, int(args[0]) if args else 20)["upper"]
        if name == "bb_lower":
            return ta_bb(d.close, int(args[0]) if args else 20)["lower"]
        if name == "bb_middle":
            return ta_bb(d.close, int(args[0]) if args else 20)["middle"]
        if name == "atr":
            return ta_atr(d.high, d.low, d.close, int(args[0]) if args else 14)
        if name == "adx":
            return ta_adx(d.high, d.low, d.close, int(args[0]) if args else 14)
        if name == "sma_volume":
            return ta_sma(d.volume, int(args[0]))
        if name == "obv":
            return ta_obv(d.close, d.volume)
        if name == "mfi":
            return ta_mfi(d.high, d.low, d.close, d.volume, int(args[0]) if args else 14)
        if name == "cmf":
            return ta_cmf(d.high, d.low, d.close, d.volume, int(args[0]) if args else 20)
        if name == "sar":
            return ta_sar(d.high, d.low)
        if name == "stochastic_k":
            k, _ = ta_stoch_rsi(d.close, int(args[0]) if args else 14)
            return k
        if name == "stochastic_d":
            _, dd = ta_stoch_rsi(d.close, int(args[0]) if args else 14)
            return dd
        raise ValueError(f"Unknown indicator function: {name}")
