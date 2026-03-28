"""Backward-compatibility shim — imports from agents.signal_engine.

The v7 suffix was removed during cleanup; this file restores the old
import path so existing tests continue to work.
"""
from agents.signal_engine import SignalEngine as SignalEngineV7, MarketRegime, SignalResult  # noqa: F401

__all__ = ["SignalEngineV7", "MarketRegime", "SignalResult"]
