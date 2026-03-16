"""Tests for AssetSelector (v9) — asset scoring and grading."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from agents.signal_engine_v9 import AssetSelector, AssetGrade, AssetScore
from tests.conftest import make_bull_prices, make_bear_prices, make_ranging_prices


@pytest.fixture
def selector():
    return AssetSelector()


class TestAssetScoring:
    def test_bull_scores_high(self, selector):
        prices = make_bull_prices(200)
        score = selector.score_asset(prices)
        assert score.composite > 0, f"Bull asset should score positive: {score.composite}"

    def test_bear_scores_low(self, selector):
        prices = make_bear_prices(200)
        score = selector.score_asset(prices)
        assert score.composite < 0.5, f"Bear asset shouldn't score high: {score.composite}"

    def test_grade_is_valid(self, selector):
        prices = make_bull_prices(200)
        score = selector.score_asset(prices)
        assert isinstance(score.grade, AssetGrade)

    def test_allocation_range(self, selector):
        prices = make_bull_prices(200)
        score = selector.score_asset(prices)
        assert 0.0 <= score.allocation_pct <= 1.0

    def test_short_data_returns_C(self, selector):
        score = selector.score_asset([100.0] * 30)
        assert score.grade == AssetGrade.C

    def test_with_volumes(self, selector):
        prices = make_bull_prices(200)
        volumes = [1_000_000] * 200
        score = selector.score_asset(prices, volumes)
        assert isinstance(score, AssetScore)

    def test_reasoning_nonempty(self, selector):
        prices = make_bull_prices(200)
        score = selector.score_asset(prices)
        assert len(score.reasoning) > 0

    def test_momentum_score_range(self, selector):
        prices = make_bull_prices(200)
        score = selector.score_asset(prices)
        assert -2.0 <= score.momentum_score <= 2.0

    def test_quality_score_range(self, selector):
        prices = make_bull_prices(200)
        score = selector.score_asset(prices)
        assert -2.0 <= score.quality_score <= 2.0

    def test_bull_grades_better_than_bear(self, selector):
        bull = selector.score_asset(make_bull_prices(200))
        bear = selector.score_asset(make_bear_prices(200))
        assert bull.composite > bear.composite
