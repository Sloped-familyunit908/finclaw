"""
Tests for FinClaw v2.1.0 — Round 10
News Sentiment, Earnings, Multi-Asset, Docker, CLI enhancements.
30+ tests covering all new modules.
"""

import sys
import os
import math
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.conftest import make_prices, make_bull_prices, make_bear_prices, make_history


# =====================================================================
# News Sentiment Pipeline Tests
# =====================================================================

class TestNewsSentimentPipeline:
    """Tests for src.ml.news_sentiment"""

    def test_import(self):
        from src.ml.news_sentiment import NewsSentimentPipeline
        p = NewsSentimentPipeline()
        assert p is not None
        assert p.sources == ["rss"]

    def test_custom_sources(self):
        from src.ml.news_sentiment import NewsSentimentPipeline
        p = NewsSentimentPipeline(sources=["rss", "custom"])
        assert p.sources == ["rss", "custom"]

    def test_analyze_sentiment_bullish(self):
        from src.ml.news_sentiment import NewsSentimentPipeline
        p = NewsSentimentPipeline()
        headlines = [
            {"title": "AAPL stock surges on strong growth and bullish momentum"},
            {"title": "Apple beats earnings estimates with record revenue"},
        ]
        score = p.analyze_sentiment(headlines)
        assert score > 0, f"Expected bullish score, got {score}"

    def test_analyze_sentiment_bearish(self):
        from src.ml.news_sentiment import NewsSentimentPipeline
        p = NewsSentimentPipeline()
        headlines = [
            {"title": "Stock crashes amid recession fears and weak earnings miss"},
            {"title": "Major decline as bankruptcy warning shakes market"},
        ]
        score = p.analyze_sentiment(headlines)
        assert score < 0, f"Expected bearish score, got {score}"

    def test_analyze_sentiment_empty(self):
        from src.ml.news_sentiment import NewsSentimentPipeline
        p = NewsSentimentPipeline()
        assert p.analyze_sentiment([]) == 0.0

    def test_analyze_sentiment_neutral(self):
        from src.ml.news_sentiment import NewsSentimentPipeline
        p = NewsSentimentPipeline()
        headlines = [{"title": "The weather is nice today in California"}]
        score = p.analyze_sentiment(headlines)
        assert score == 0.0

    def test_get_signal_structure(self):
        from src.ml.news_sentiment import NewsSentimentPipeline
        p = NewsSentimentPipeline(feeds={})  # empty feeds = no network calls
        signal = p.get_signal("AAPL")
        assert "ticker" in signal
        assert "sentiment" in signal
        assert "headlines" in signal
        assert "signal" in signal
        assert signal["ticker"] == "AAPL"
        assert signal["signal"] in ("bullish", "bearish", "neutral")

    def test_get_signal_with_mocked_headlines(self):
        from src.ml.news_sentiment import NewsSentimentPipeline
        p = NewsSentimentPipeline(feeds={})
        with patch.object(p, "fetch_headlines", return_value=[
            {"title": "Stock surges on bullish momentum rally"},
            {"title": "Strong growth beats expectations"},
        ]):
            signal = p.get_signal("TSLA")
            assert signal["signal"] == "bullish"
            assert signal["sentiment"] > 0

    def test_fetch_headlines_no_network(self):
        from src.ml.news_sentiment import NewsSentimentPipeline
        p = NewsSentimentPipeline(feeds={"bad": "http://localhost:1/bad"}, timeout=1)
        result = p.fetch_headlines("AAPL")
        assert isinstance(result, list)  # Should not crash


# =====================================================================
# Earnings Calendar Tests
# =====================================================================

class TestEarningsCalendar:
    """Tests for src.data.earnings"""

    def test_import(self):
        from src.data.earnings import EarningsCalendar
        cal = EarningsCalendar()
        assert cal is not None

    def test_custom_watchlist(self):
        from src.data.earnings import EarningsCalendar
        cal = EarningsCalendar(watchlist=["AAPL", "MSFT"])
        assert cal.watchlist == ["AAPL", "MSFT"]

    def test_upcoming_returns_list(self):
        from src.data.earnings import EarningsCalendar
        cal = EarningsCalendar(watchlist=[])
        result = cal.upcoming(days=7)
        assert isinstance(result, list)

    def test_historical_returns_list(self):
        from src.data.earnings import EarningsCalendar
        cal = EarningsCalendar()
        # Mock yfinance to avoid network calls
        with patch("src.data.earnings.yf") as mock_yf:
            mock_ticker = MagicMock()
            mock_ticker.earnings_history = None
            mock_ticker.quarterly_earnings = MagicMock()
            mock_ticker.quarterly_earnings.empty = True
            mock_yf.Ticker.return_value = mock_ticker
            result = cal.historical("AAPL", quarters=4)
            assert isinstance(result, list)

    def test_surprise_history_returns_list(self):
        from src.data.earnings import EarningsCalendar
        cal = EarningsCalendar()
        with patch.object(cal, "historical", return_value=[
            {"date": "2024-01-01", "surprise_pct": 5.2, "eps_actual": 1.5, "eps_estimate": 1.42},
            {"date": "2024-04-01", "surprise_pct": -2.1, "eps_actual": 1.3, "eps_estimate": 1.33},
        ]):
            result = cal.surprise_history("AAPL")
            assert len(result) == 2
            assert result[0]["beat"] is True
            assert result[1]["beat"] is False

    def test_earnings_event_dataclass(self):
        from src.data.earnings import EarningsEvent
        ev = EarningsEvent(ticker="AAPL", date="2024-01-01", eps_actual=1.5, surprise_pct=5.0)
        assert ev.ticker == "AAPL"
        assert ev.surprise_pct == 5.0


# =====================================================================
# Multi-Asset Fetcher Tests
# =====================================================================

class TestMultiAssetFetcher:
    """Tests for src.data.multi_asset"""

    def test_import(self):
        from src.data.multi_asset import MultiAssetFetcher
        f = MultiAssetFetcher()
        assert f is not None

    def test_list_available(self):
        from src.data.multi_asset import MultiAssetFetcher
        avail = MultiAssetFetcher.list_available()
        assert "crypto" in avail
        assert "forex" in avail
        assert "commodity" in avail
        assert "index" in avail
        assert "BTC" in avail["crypto"]
        assert "EURUSD" in avail["forex"]

    def test_symbol_mappings(self):
        from src.data.multi_asset import CRYPTO_SYMBOLS, FOREX_SYMBOLS, COMMODITY_SYMBOLS, INDEX_SYMBOLS
        assert CRYPTO_SYMBOLS["BTC"] == "BTC-USD"
        assert FOREX_SYMBOLS["EURUSD"] == "EURUSD=X"
        assert COMMODITY_SYMBOLS["gold"] == "GC=F"
        assert INDEX_SYMBOLS["SP500"] == "^GSPC"

    def test_unknown_commodity_raises(self):
        from src.data.multi_asset import MultiAssetFetcher
        f = MultiAssetFetcher()
        with pytest.raises(ValueError, match="Unknown commodity"):
            f.get_commodity("unobtanium")

    def test_unknown_index_raises(self):
        from src.data.multi_asset import MultiAssetFetcher
        f = MultiAssetFetcher()
        with pytest.raises(ValueError, match="Unknown index"):
            f.get_index("FAKE_INDEX")

    def test_get_any_unknown_type(self):
        from src.data.multi_asset import MultiAssetFetcher
        f = MultiAssetFetcher()
        with pytest.raises(ValueError, match="Unknown asset_type"):
            f.get_any("BTC", asset_type="nft")

    def test_custom_period(self):
        from src.data.multi_asset import MultiAssetFetcher
        f = MultiAssetFetcher(period="6mo")
        assert f.period == "6mo"


# =====================================================================
# Sentiment (existing module) Tests
# =====================================================================

class TestSimpleSentiment:
    """Additional tests for src.ml.sentiment"""

    def test_analyze_empty(self):
        from src.ml.sentiment import SimpleSentiment
        s = SimpleSentiment()
        assert s.analyze("") == 0.0

    def test_analyze_bullish_keyword(self):
        from src.ml.sentiment import SimpleSentiment
        s = SimpleSentiment()
        score = s.analyze("bullish rally growth")
        assert score > 0

    def test_analyze_bearish_keyword(self):
        from src.ml.sentiment import SimpleSentiment
        s = SimpleSentiment()
        score = s.analyze("crash decline bankruptcy")
        assert score < 0

    def test_analyze_batch(self):
        from src.ml.sentiment import SimpleSentiment
        s = SimpleSentiment()
        scores = s.analyze_batch(["bullish rally", "crash decline", ""])
        assert len(scores) == 3
        assert scores[0] > 0
        assert scores[1] < 0
        assert scores[2] == 0.0

    def test_get_keywords_found(self):
        from src.ml.sentiment import SimpleSentiment
        s = SimpleSentiment()
        found = s.get_keywords_found("bullish growth crash")
        assert "bullish" in found
        assert "growth" in found
        assert "crash" in found

    def test_custom_words(self):
        from src.ml.sentiment import SimpleSentiment
        s = SimpleSentiment(bullish_words={"moon": 1.0}, bearish_words={"rekt": -1.0})
        assert s.analyze("moon") == 1.0
        assert s.analyze("rekt") == -1.0


# =====================================================================
# Docker Files Tests
# =====================================================================

class TestDockerFiles:
    """Verify Docker configuration files exist and are valid."""

    def test_dockerfile_exists(self):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Dockerfile")
        assert os.path.exists(path), "Dockerfile not found"

    def test_dockerfile_has_from(self):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Dockerfile")
        content = open(path).read()
        assert "FROM" in content
        assert "python" in content.lower()

    def test_docker_compose_exists(self):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docker-compose.yml")
        assert os.path.exists(path), "docker-compose.yml not found"

    def test_docker_compose_valid_yaml(self):
        import yaml
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docker-compose.yml")
        with open(path) as f:
            data = yaml.safe_load(f)
        assert "services" in data
        assert "finclaw" in data["services"]


# =====================================================================
# CLI Backtest Enhancement Tests
# =====================================================================

class TestCLIEnhancements:
    """Test enhanced CLI backtest features."""

    def test_cli_entry_point_exists(self):
        """Verify finclaw.py has main() entry point."""
        import finclaw
        assert hasattr(finclaw, "main")

    def test_strategies_dict(self):
        from finclaw import STRATEGIES
        assert "momentum" in STRATEGIES
        assert "mean_reversion" in STRATEGIES
        assert "buffett" in STRATEGIES
        assert len(STRATEGIES) >= 8

    def test_strategy_has_required_keys(self):
        from finclaw import STRATEGIES
        for name, s in STRATEGIES.items():
            assert "desc" in s, f"{name} missing desc"
            assert "risk" in s, f"{name} missing risk"
            assert "select" in s, f"{name} missing select"
            assert "alloc" in s, f"{name} missing alloc"


# =====================================================================
# Momentum Strategy Tests
# =====================================================================

class TestMomentumStrategy:
    """Tests for strategies.momentum_jt"""

    def test_score_single_bullish(self):
        from src.strategies.momentum_jt import MomentumJTStrategy
        s = MomentumJTStrategy()
        prices = make_bull_prices(n=400)
        score = s.score_single(prices)
        assert score.signal == "buy"
        assert score.momentum_12m > 0

    def test_score_single_bearish(self):
        from src.strategies.momentum_jt import MomentumJTStrategy
        s = MomentumJTStrategy()
        # Create a strongly bearish series
        prices = make_prices(start=100, n=400, trend=-0.003, volatility=0.01, seed=42)
        score = s.score_single(prices)
        assert score.momentum_12m < 0

    def test_score_single_insufficient_data(self):
        from src.strategies.momentum_jt import MomentumJTStrategy
        s = MomentumJTStrategy()
        score = s.score_single([100, 101, 102])
        assert score.signal == "hold"

    def test_rank_assets(self):
        from src.strategies.momentum_jt import MomentumJTStrategy
        s = MomentumJTStrategy()
        assets = {
            "BULL": make_bull_prices(n=400, seed=1),
            "BEAR": make_bear_prices(n=400, seed=2),
            "FLAT": make_prices(n=400, trend=0.0, seed=3),
        }
        ranked = s.rank_assets(assets)
        assert len(ranked) == 3
        assert ranked[0].rank == 1
        # Bull should rank higher than bear
        bull_rank = next(r for r in ranked if r.symbol == "BULL")
        bear_rank = next(r for r in ranked if r.symbol == "BEAR")
        assert bull_rank.rank < bear_rank.rank
