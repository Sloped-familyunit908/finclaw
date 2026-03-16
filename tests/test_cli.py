"""Tests for finclaw.py CLI module — strategies, universes, utilities."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from finclaw import STRATEGIES, UNIVERSES


class TestStrategies:
    def test_all_strategies_have_required_keys(self):
        required = {"desc", "risk", "target_ann", "select", "alloc"}
        for name, strat in STRATEGIES.items():
            assert required.issubset(strat.keys()), f"{name} missing keys"

    def test_select_is_callable(self):
        for name, strat in STRATEGIES.items():
            assert callable(strat["select"]), f"{name}.select not callable"

    def test_alloc_valid_values(self):
        valid = {"equal", "grade", "risk_parity"}
        for name, strat in STRATEGIES.items():
            assert strat["alloc"] in valid, f"{name}.alloc invalid"

    def test_at_least_8_strategies(self):
        assert len(STRATEGIES) >= 8


class TestUniverses:
    def test_us_universe_nonempty(self):
        assert len(UNIVERSES["us"]) > 20

    def test_china_universe_nonempty(self):
        assert len(UNIVERSES["china"]) > 20

    def test_hk_universe_nonempty(self):
        assert len(UNIVERSES["hk"]) > 10

    def test_all_tickers_are_strings(self):
        for market, tickers in UNIVERSES.items():
            for ticker in tickers:
                assert isinstance(ticker, str), f"{market}: {ticker} not str"

    def test_all_names_are_strings(self):
        for market, tickers in UNIVERSES.items():
            for ticker, name in tickers.items():
                assert isinstance(name, str), f"{market}: {ticker} name not str"


class TestStrategySelection:
    """Test that strategy select functions work with mock data."""

    def _mock_data(self, n=20):
        import random
        rng = random.Random(42)
        return [
            {
                "ticker": f"T{i}", "name": f"Stock{i}",
                "wt_ann": rng.uniform(-0.1, 0.4),
                "recent_1y": rng.uniform(-0.2, 0.5),
                "cagr_3y": rng.uniform(-0.1, 0.3),
                "ann_vol": rng.uniform(0.1, 0.5),
                "max_dd_peak": rng.uniform(-0.5, -0.05),
                "composite": rng.uniform(0, 1),
                "grade": "A",
            }
            for i in range(n)
        ]

    def test_druckenmiller_selects_3(self):
        result = STRATEGIES["druckenmiller"]["select"](self._mock_data())
        assert len(result) == 3

    def test_soros_selects_up_to_5(self):
        result = STRATEGIES["soros"]["select"](self._mock_data())
        assert 1 <= len(result) <= 5

    def test_conservative_selects_up_to_15(self):
        result = STRATEGIES["conservative"]["select"](self._mock_data())
        assert 1 <= len(result) <= 15

    def test_balanced_selects_up_to_10(self):
        result = STRATEGIES["balanced"]["select"](self._mock_data())
        assert 1 <= len(result) <= 10
