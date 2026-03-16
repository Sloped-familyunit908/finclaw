"""Tests for macro_analyzer.py — macro regime detection."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from agents.macro_analyzer import MacroRegime


class TestMacroRegime:
    def test_regime_enum_values(self):
        assert MacroRegime.RISK_ON.value == "risk_on"
        assert MacroRegime.RISK_OFF.value == "risk_off"
        assert MacroRegime.INFLATION.value == "inflation"
        assert MacroRegime.DEFLATION.value == "deflation"
        assert MacroRegime.TRANSITION.value == "transition"

    def test_all_regimes_unique(self):
        values = [r.value for r in MacroRegime]
        assert len(values) == len(set(values))
