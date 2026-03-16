"""Tests for stock_picker.py — MultiFactorPicker."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from agents.stock_picker import MultiFactorPicker, ConvictionLevel, StockAnalysis
from tests.conftest import make_bull_prices, make_bear_prices, make_history


@pytest.fixture
def picker():
    return MultiFactorPicker(use_fundamentals=False, use_llm=False)


class TestMultiFactorPicker:
    def test_analyze_returns_stock_analysis(self, picker):
        h = make_history(make_bull_prices(200))
        result = picker.analyze("TEST", h, name="TestCo")
        assert isinstance(result, StockAnalysis)

    def test_conviction_is_valid_enum(self, picker):
        h = make_history(make_bull_prices(200))
        result = picker.analyze("TEST", h, name="TestCo")
        assert isinstance(result.conviction, ConvictionLevel)

    def test_score_range(self, picker):
        h = make_history(make_bull_prices(200))
        result = picker.analyze("TEST", h, name="TestCo")
        assert -2.0 <= result.score <= 2.0

    def test_factors_present(self, picker):
        h = make_history(make_bull_prices(200))
        result = picker.analyze("TEST", h, name="TestCo")
        assert isinstance(result.factors, dict)

    def test_bull_scores_higher_than_bear(self, picker):
        bull = picker.analyze("BULL", make_history(make_bull_prices(200)), name="Bull")
        bear = picker.analyze("BEAR", make_history(make_bear_prices(200)), name="Bear")
        assert bull.score > bear.score
