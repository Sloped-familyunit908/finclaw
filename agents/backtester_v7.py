"""Backward-compatibility shim — imports from agents.backtester.

The v7 suffix was removed during cleanup; this file restores the old
import path so existing tests continue to work.
"""
from agents.backtester import Backtester as BacktesterV7, BacktestResult, Trade  # noqa: F401

__all__ = ["BacktesterV7", "BacktestResult", "Trade"]
