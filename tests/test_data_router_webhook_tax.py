"""
Tests for FinClaw v3.5.0 — Data Router, Webhook, Tax Calculator, Benchmark Comparator.
35 tests total.
"""

import json
import math
import pytest
from unittest.mock import patch, MagicMock

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ═══════════════════════════════════════════════════════════
# Data Router Tests (10)
# ═══════════════════════════════════════════════════════════

from src.data.data_router import (
    DataRouter, DataProvider, MockProvider, YahooProvider, AlphaVantageProvider,
)


class TestMockProvider:
    def test_ohlcv_generates_data(self):
        p = MockProvider()
        data = p.get_ohlcv("AAPL", "2024-01-01", "2024-01-31")
        assert "dates" in data
        assert "close" in data
        assert len(data["dates"]) > 0
        assert data["source"] == "mock"

    def test_ohlcv_seeded(self):
        p = MockProvider()
        p.seed("TSLA", ohlcv={"dates": ["2024-01-02"], "close": [250.0]})
        data = p.get_ohlcv("TSLA", "2024-01-01", "2024-01-31")
        assert data["close"] == [250.0]
        assert data["source"] == "mock"

    def test_realtime_returns_price(self):
        p = MockProvider()
        data = p.get_realtime("AAPL")
        assert "price" in data
        assert isinstance(data["price"], float)

    def test_realtime_seeded(self):
        p = MockProvider()
        p.seed("MSFT", realtime={"price": 420.0, "volume": 999})
        data = p.get_realtime("MSFT")
        assert data["price"] == 420.0

    def test_health_check_always_true(self):
        assert MockProvider().health_check() is True


class TestDataRouter:
    def test_default_providers_include_mock(self):
        # With only mock (yahoo/alpha_vantage won't work in tests)
        router = DataRouter(providers=["mock"])
        assert "mock" in router.provider_order

    def test_get_ohlcv_from_mock(self):
        router = DataRouter(providers=["mock"])
        data = router.get_ohlcv("AAPL", "2024-01-01", "2024-02-01")
        assert data["source"] == "mock"
        assert len(data["close"]) > 0

    def test_get_realtime_from_mock(self):
        router = DataRouter(providers=["mock"])
        data = router.get_realtime("GOOG")
        assert "price" in data

    def test_fallback_on_failure(self):
        """First provider fails, falls back to mock."""
        class FailProvider(DataProvider):
            def get_ohlcv(self, *a): raise RuntimeError("down")
            def get_realtime(self, *a): raise RuntimeError("down")
            def health_check(self): return False

        router = DataRouter(providers=["mock"])
        router._providers = {"fail": FailProvider(), "mock": MockProvider()}
        data = router.get_ohlcv("AAPL", "2024-01-01", "2024-01-31")
        assert data["source"] == "mock"

    def test_all_fail_raises(self):
        class FailProvider(DataProvider):
            def get_ohlcv(self, *a): raise RuntimeError("fail")
            def get_realtime(self, *a): raise RuntimeError("fail")
            def health_check(self): return False

        router = DataRouter(providers=[])
        router._providers = {"fail": FailProvider()}
        with pytest.raises(RuntimeError, match="All providers failed"):
            router.get_ohlcv("XYZ", "2024-01-01", "2024-01-31")

    def test_add_provider(self):
        router = DataRouter(providers=["mock"])
        custom = MockProvider()
        router.add_provider("custom", custom)
        assert "custom" in router.provider_order

    def test_health_check(self):
        router = DataRouter(providers=["mock"])
        status = router.health_check()
        assert status["mock"] is True


# ═══════════════════════════════════════════════════════════
# Webhook Notifier Tests (8)
# ═══════════════════════════════════════════════════════════

from src.notifications.webhook import WebhookNotifier


class TestWebhookNotifier:
    def test_format_slack(self):
        wn = WebhookNotifier({"slack": "https://hooks.slack.com/test"})
        payload = wn.format_slack({"event": "alert", "ticker": "AAPL", "price": 150})
        assert "blocks" in payload
        assert payload["text"] == "FinClaw: alert"

    def test_format_discord(self):
        wn = WebhookNotifier({"discord": "https://discord.com/api/webhooks/test"})
        payload = wn.format_discord({"event": "alert", "ticker": "AAPL"})
        assert "embeds" in payload
        assert payload["embeds"][0]["title"] == "🦀 FinClaw: alert"
        assert payload["embeds"][0]["color"] == 0x00D4AA

    @patch("src.notifications.webhook.requests.post")
    def test_notify_success(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        wn = WebhookNotifier({"custom": "https://example.com/hook"})
        results = wn.notify("price_alert", {"ticker": "TSLA", "price": 300})
        assert results["custom"] is True
        mock_post.assert_called_once()

    @patch("src.notifications.webhook.requests.post")
    def test_notify_failure_status(self, mock_post):
        mock_post.return_value = MagicMock(status_code=500, text="error")
        wn = WebhookNotifier({"custom": "https://example.com/hook"})
        results = wn.notify("test", {})
        assert results["custom"] is False

    @patch("src.notifications.webhook.requests.post", side_effect=Exception("timeout"))
    def test_notify_exception(self, mock_post):
        wn = WebhookNotifier({"custom": "https://example.com/hook"})
        results = wn.notify("test", {})
        assert results["custom"] is False

    @patch("src.notifications.webhook.requests.post")
    def test_notify_multiple_webhooks(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        wn = WebhookNotifier({
            "slack": "https://hooks.slack.com/x",
            "discord": "https://discord.com/api/webhooks/x",
        })
        results = wn.notify("test", {"data": "value"})
        assert results["slack"] is True
        assert results["discord"] is True
        assert mock_post.call_count == 2

    def test_add_remove_webhook(self):
        wn = WebhookNotifier({"slack": "https://a"})
        wn.add_webhook("custom", "https://b")
        assert "custom" in wn.webhooks
        wn.remove_webhook("custom")
        assert "custom" not in wn.webhooks

    def test_empty_webhooks(self):
        wn = WebhookNotifier({})
        results = wn.notify("test", {})
        assert results == {}


# ═══════════════════════════════════════════════════════════
# Tax Calculator Tests (10)
# ═══════════════════════════════════════════════════════════

from src.analytics.tax_calculator import TaxCalculator, TaxLot


class TestTaxLot:
    def test_short_term(self):
        lot = TaxLot("AAPL", "2024-01-01", 100.0, 10, "2024-06-01", 150.0)
        assert not lot.is_long_term
        assert lot.gain == 500.0

    def test_long_term(self):
        lot = TaxLot("AAPL", "2023-01-01", 100.0, 10, "2024-06-01", 150.0)
        assert lot.is_long_term

    def test_no_sell(self):
        lot = TaxLot("AAPL", "2024-01-01", 100.0, 10)
        assert lot.gain == 0.0
        assert not lot.is_long_term

    def test_cost_basis(self):
        lot = TaxLot("AAPL", "2024-01-01", 150.0, 20)
        assert lot.cost_basis == 3000.0


class TestTaxCalculator:
    def _sample_trades(self):
        return [
            {"ticker": "AAPL", "action": "buy", "date": "2024-01-15", "price": 100.0, "shares": 50},
            {"ticker": "AAPL", "action": "sell", "date": "2024-06-15", "price": 120.0, "shares": 50},
        ]

    def test_basic_short_term_gain(self):
        calc = TaxCalculator("US")
        result = calc.calculate(self._sample_trades())
        assert result["short_term_gains"] == 1000.0  # (120-100)*50
        assert result["long_term_gains"] == 0.0
        assert result["total_tax"] > 0

    def test_long_term_gain(self):
        trades = [
            {"ticker": "GOOG", "action": "buy", "date": "2022-01-01", "price": 100.0, "shares": 10},
            {"ticker": "GOOG", "action": "sell", "date": "2024-06-01", "price": 200.0, "shares": 10},
        ]
        result = TaxCalculator("US").calculate(trades)
        assert result["long_term_gains"] == 1000.0
        assert result["short_term_gains"] == 0.0

    def test_wash_sale_detected(self):
        trades = [
            {"ticker": "TSLA", "action": "buy", "date": "2024-01-01", "price": 200.0, "shares": 10},
            {"ticker": "TSLA", "action": "sell", "date": "2024-03-01", "price": 150.0, "shares": 10},
            {"ticker": "TSLA", "action": "buy", "date": "2024-03-15", "price": 155.0, "shares": 10},
        ]
        result = TaxCalculator("US").calculate(trades)
        assert len(result["wash_sales"]) > 0
        assert result["wash_sales"][0]["disallowed_loss"] == 500.0

    def test_no_trades(self):
        result = TaxCalculator("US").calculate([])
        assert result["short_term_gains"] == 0.0
        assert result["total_tax"] == 0.0

    def test_uk_jurisdiction(self):
        calc = TaxCalculator("UK")
        assert calc.rates["short_term"] == 0.20

    def test_optimize_harvesting(self):
        calc = TaxCalculator("US")
        portfolio = {
            "AAPL": {"shares": 100, "cost_basis": 180.0, "current_price": 150.0},
            "GOOG": {"shares": 50, "cost_basis": 140.0, "current_price": 130.0},
            "MSFT": {"shares": 200, "cost_basis": 300.0, "current_price": 310.0},
        }
        suggestions = calc.optimize_harvesting(portfolio, 2000.0)
        assert len(suggestions) >= 1
        # AAPL has biggest loss (30*100=3000), should be first
        assert suggestions[0]["ticker"] == "AAPL"
        assert "MSFT" not in [s["ticker"] for s in suggestions]  # MSFT has gain


# ═══════════════════════════════════════════════════════════
# Benchmark Comparator Tests (7)
# ═══════════════════════════════════════════════════════════

from src.analytics.benchmark import BenchmarkComparator


class TestBenchmarkComparator:
    def _returns(self, n=100, mu=0.001, sigma=0.02):
        import random
        random.seed(123)
        return [random.gauss(mu, sigma) for _ in range(n)]

    def test_compare_basic(self):
        bc = BenchmarkComparator()
        sr = self._returns(100, 0.001, 0.02)
        br = self._returns(100, 0.0005, 0.015)
        result = bc.compare(sr, br, "SPY")
        assert "alpha" in result
        assert "beta" in result
        assert result["periods"] == 100
        assert result["benchmark"] == "SPY"

    def test_compare_with_mock_benchmark(self):
        bc = BenchmarkComparator()
        sr = self._returns(50)
        result = bc.compare(sr, benchmark="QQQ")
        assert result["periods"] == 50
        assert result["benchmark_name"] == "NASDAQ"

    def test_empty_returns(self):
        bc = BenchmarkComparator()
        result = bc.compare([], [], "SPY")
        assert result["alpha"] == 0.0
        assert result["periods"] == 0

    def test_single_return(self):
        bc = BenchmarkComparator()
        result = bc.compare([0.01], [0.005])
        assert result["periods"] == 0  # n < 2

    def test_capture_ratios(self):
        bc = BenchmarkComparator()
        sr = [0.02, -0.01, 0.03, -0.02, 0.01]
        br = [0.01, -0.02, 0.02, -0.01, 0.015]
        result = bc.compare(sr, br)
        assert isinstance(result["up_capture"], float)
        assert isinstance(result["down_capture"], float)

    def test_render_chart_without_compare(self):
        bc = BenchmarkComparator()
        html = bc.render_comparison_chart()
        assert "No comparison data" in html

    def test_render_chart_after_compare(self):
        bc = BenchmarkComparator()
        sr = self._returns(50)
        bc.compare(sr, benchmark="SPY")
        html = bc.render_comparison_chart()
        assert "FinClaw Benchmark Comparison" in html
        assert "S&P 500" in html
        assert "Alpha" in html
