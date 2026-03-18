"""Comprehensive coverage tests for under-tested modules.

Covers:
- TradeJournal (paper trading journal)
- DataExporter (multi-format export)
- ConfigManager (configuration management)
- OrderRouter (execution routing)
- YieldCurve (fixed income)
- DeploymentConfig (deployment)
"""

import json
import os
import time

import pytest


# ══════════════════════════════════════════════════════════════════
# TradeJournal
# ══════════════════════════════════════════════════════════════════

class TestTradeJournal:
    def test_record_trade(self):
        from src.paper.journal import TradeJournal
        j = TradeJournal()
        j.record_trade({"symbol": "AAPL", "side": "BUY", "quantity": 10, "price": 150.0,
                         "timestamp": time.time()}, reason="Breakout signal")
        assert len(j.get_entries()) == 1
        assert j.get_entries()[0]["symbol"] == "AAPL"

    def test_add_note(self):
        from src.paper.journal import TradeJournal
        j = TradeJournal()
        j.add_note("Market looks bullish today")
        notes = j.get_notes()
        assert len(notes) == 1
        assert "bullish" in notes[0]["text"]

    def test_multiple_trades(self):
        from src.paper.journal import TradeJournal
        j = TradeJournal()
        for i in range(5):
            j.record_trade({"symbol": f"S{i}", "side": "BUY", "quantity": i + 1,
                             "price": 100 + i, "timestamp": time.time()})
        assert len(j.get_entries()) == 5

    def test_daily_summary(self):
        from src.paper.journal import TradeJournal
        from datetime import datetime
        j = TradeJournal()
        j.record_trade({"symbol": "AAPL", "side": "BUY", "quantity": 10,
                         "price": 150.0, "timestamp": time.time()})
        summary = j.daily_summary(datetime.now().strftime("%Y-%m-%d"))
        assert "AAPL" in summary
        assert "BUY" in summary

    def test_daily_summary_empty(self):
        from src.paper.journal import TradeJournal
        j = TradeJournal()
        summary = j.daily_summary("2020-01-01")
        assert "No activity" in summary

    def test_export_csv(self):
        from src.paper.journal import TradeJournal
        j = TradeJournal()
        j.record_trade({"symbol": "AAPL", "side": "BUY", "quantity": 10,
                         "price": 150.0, "timestamp": time.time()})
        csv_out = j.export("csv")
        assert "AAPL" in csv_out
        assert "timestamp" in csv_out

    def test_export_json(self):
        from src.paper.journal import TradeJournal
        j = TradeJournal()
        j.record_trade({"symbol": "MSFT", "side": "SELL", "quantity": 5,
                         "price": 400.0, "timestamp": time.time()})
        json_out = j.export("json")
        parsed = json.loads(json_out)
        assert isinstance(parsed, list)
        assert len(parsed) >= 1

    def test_performance_review(self):
        from src.paper.journal import TradeJournal
        j = TradeJournal()
        j.record_trade({"symbol": "AAPL", "side": "BUY", "quantity": 10,
                         "price": 150.0, "timestamp": time.time()})
        j.record_trade({"symbol": "AAPL", "side": "SELL", "quantity": 10,
                         "price": 160.0, "pnl": 100.0, "timestamp": time.time()})
        review = j.performance_review("1w")
        assert review["total_trades"] == 2
        assert review["total_pnl"] == 100.0
        assert review["win_count"] == 1

    def test_persistence(self, tmp_path):
        from src.paper.journal import TradeJournal
        path = str(tmp_path / "journal.json")
        j = TradeJournal(journal_path=path)
        j.record_trade({"symbol": "GOOGL", "side": "BUY", "quantity": 5,
                         "price": 2800.0, "timestamp": time.time()})
        # Reload
        j2 = TradeJournal(journal_path=path)
        assert len(j2.get_entries()) == 1
        assert j2.get_entries()[0]["symbol"] == "GOOGL"


# ══════════════════════════════════════════════════════════════════
# DataExporter
# ══════════════════════════════════════════════════════════════════

class TestDataExporter:
    def _sample_data(self):
        return [
            {"symbol": "AAPL", "price": 150.0, "volume": 1000000},
            {"symbol": "MSFT", "price": 400.0, "volume": 500000},
        ]

    def test_to_csv(self, tmp_path):
        from src.export.exporter import DataExporter
        exp = DataExporter()
        path = str(tmp_path / "test.csv")
        result = exp.to_csv(self._sample_data(), path)
        assert os.path.exists(result)
        with open(result) as f:
            content = f.read()
        assert "AAPL" in content
        assert "MSFT" in content

    def test_to_json(self, tmp_path):
        from src.export.exporter import DataExporter
        exp = DataExporter()
        path = str(tmp_path / "test.json")
        result = exp.to_json(self._sample_data(), path)
        assert os.path.exists(result)
        with open(result) as f:
            data = json.load(f)
        assert len(data) == 2

    def test_to_string_csv(self):
        from src.export.exporter import DataExporter
        exp = DataExporter()
        csv_str = exp.to_string(self._sample_data(), "csv")
        assert "symbol" in csv_str
        assert "AAPL" in csv_str

    def test_to_string_json(self):
        from src.export.exporter import DataExporter
        exp = DataExporter()
        json_str = exp.to_string(self._sample_data(), "json")
        parsed = json.loads(json_str)
        assert len(parsed) == 2

    def test_empty_data_raises(self, tmp_path):
        from src.export.exporter import DataExporter
        exp = DataExporter()
        with pytest.raises(ValueError):
            exp.to_csv([], str(tmp_path / "empty.csv"))

    def test_single_dict(self, tmp_path):
        from src.export.exporter import DataExporter
        exp = DataExporter()
        path = str(tmp_path / "single.csv")
        exp.to_csv({"symbol": "AAPL", "price": 150}, path)
        assert os.path.exists(path)

    def test_empty_to_string(self):
        from src.export.exporter import DataExporter
        exp = DataExporter()
        result = exp.to_string([], "csv")
        assert result == ""


# ══════════════════════════════════════════════════════════════════
# ConfigManager
# ══════════════════════════════════════════════════════════════════

class TestConfigManager:
    def test_default_config(self):
        from src.config_manager import ConfigManager
        cm = ConfigManager()
        assert cm.get("backtest.commission") == 0.001
        assert cm.get("risk.max_position_pct") == 0.10

    def test_get_missing_key(self):
        from src.config_manager import ConfigManager
        cm = ConfigManager()
        assert cm.get("nonexistent.key") is None
        assert cm.get("nonexistent.key", 42) == 42

    def test_set_value(self):
        from src.config_manager import ConfigManager
        cm = ConfigManager()
        cm.set("backtest.commission", 0.002)
        assert cm.get("backtest.commission") == 0.002

    def test_set_nested(self):
        from src.config_manager import ConfigManager
        cm = ConfigManager()
        cm.set("custom.nested.key", "value")
        assert cm.get("custom.nested.key") == "value"

    def test_validate_valid(self):
        from src.config_manager import ConfigManager
        cm = ConfigManager()
        result = cm.validate()  # Should not raise
        assert result is None or result is True, "validate() on valid config should succeed"

    def test_validate_invalid(self):
        from src.config_manager import ConfigManager, ConfigValidationError
        cm = ConfigManager()
        cm.set("backtest.commission", 5.0)  # Out of range
        with pytest.raises(ConfigValidationError):
            cm.validate()

    def test_to_dict(self):
        from src.config_manager import ConfigManager
        cm = ConfigManager()
        d = cm.to_dict()
        assert isinstance(d, dict)
        assert "backtest" in d

    def test_strategy_config(self):
        from src.config_manager import ConfigManager
        cm = ConfigManager()
        momentum = cm.get_strategy_config("momentum")
        assert "lookback" in momentum

    def test_save_and_load(self, tmp_path):
        from src.config_manager import ConfigManager
        path = str(tmp_path / "config.yml")
        cm = ConfigManager()
        cm.set("backtest.commission", 0.005)
        cm.save(path)
        cm2 = ConfigManager.load(path)
        assert cm2.get("backtest.commission") == 0.005

    def test_load_nonexistent_returns_defaults(self):
        from src.config_manager import ConfigManager
        cm = ConfigManager.load("/nonexistent/path/config.yml")
        assert cm.get("backtest.initial_capital") == 100000


# ══════════════════════════════════════════════════════════════════
# OrderRouter
# ══════════════════════════════════════════════════════════════════

class TestOrderRouter:
    def test_submit_market_order(self):
        from src.execution.order_router import OrderRouter, Order, OrderStatus
        router = OrderRouter()
        order = Order(symbol="AAPL", quantity=10, side="buy")
        result = router.submit(order, market_price=150.0)
        assert result.status == OrderStatus.FILLED
        assert result.fill_price == 150.0
        assert result.filled_quantity == 10

    def test_submit_limit_order(self):
        from src.execution.order_router import OrderRouter, Order, OrderStatus
        router = OrderRouter()
        order = Order(symbol="AAPL", quantity=5, side="buy",
                      order_type="limit", limit_price=145.0)
        result = router.submit(order)
        assert result.status == OrderStatus.FILLED

    def test_unknown_venue_rejected(self):
        from src.execution.order_router import OrderRouter, Order, OrderStatus
        router = OrderRouter()
        order = Order(symbol="AAPL", quantity=10, venue="nonexistent")
        result = router.submit(order)
        assert result.status == OrderStatus.REJECTED

    def test_get_status(self):
        from src.execution.order_router import OrderRouter, Order, OrderStatus
        router = OrderRouter()
        order = Order(symbol="AAPL", quantity=10)
        router.submit(order, market_price=150.0)
        status = router.get_status(order.order_id)
        assert status == OrderStatus.FILLED

    def test_get_status_nonexistent(self):
        from src.execution.order_router import OrderRouter
        router = OrderRouter()
        assert router.get_status("fake-id") is None

    def test_all_results(self):
        from src.execution.order_router import OrderRouter, Order
        router = OrderRouter()
        for i in range(3):
            router.submit(Order(symbol=f"S{i}", quantity=1), market_price=100.0)
        assert len(router.all_results()) == 3

    def test_register_custom_venue(self):
        from src.execution.order_router import OrderRouter, Order, OrderResult, OrderStatus

        class CustomVenue:
            def execute(self, order, market_price=None):
                return OrderResult(
                    order_id=order.order_id,
                    status=OrderStatus.FILLED,
                    fill_price=999.0,
                    filled_quantity=order.quantity,
                )

        router = OrderRouter()
        router.register_venue("custom", CustomVenue())
        order = Order(symbol="BTC", quantity=1, venue="custom")
        result = router.submit(order)
        assert result.fill_price == 999.0

    def test_sell_order(self):
        from src.execution.order_router import OrderRouter, Order, OrderStatus
        router = OrderRouter()
        order = Order(symbol="AAPL", quantity=10, side="sell")
        result = router.submit(order, market_price=155.0)
        assert result.status == OrderStatus.FILLED
        assert result.fill_price == 155.0


# ══════════════════════════════════════════════════════════════════
# YieldCurve
# ══════════════════════════════════════════════════════════════════

class TestYieldCurve:
    def _make_curve(self):
        from src.fixed_income.yield_curve import YieldCurve
        tenors = [0.25, 0.5, 1, 2, 5, 10, 30]
        rates = [0.045, 0.046, 0.047, 0.043, 0.040, 0.038, 0.037]
        return YieldCurve(tenors, rates)

    def test_interpolate_at_node(self):
        curve = self._make_curve()
        assert curve.interpolate(1.0) == pytest.approx(0.047)

    def test_interpolate_between_nodes(self):
        curve = self._make_curve()
        rate = curve.interpolate(1.5)
        assert 0.043 < rate < 0.047

    def test_interpolate_before_first(self):
        curve = self._make_curve()
        assert curve.interpolate(0.1) == pytest.approx(0.045)

    def test_interpolate_after_last(self):
        curve = self._make_curve()
        assert curve.interpolate(40.0) == pytest.approx(0.037)

    def test_forward_rate(self):
        curve = self._make_curve()
        fwd = curve.forward_rate(1.0, 2.0)
        assert isinstance(fwd, float)

    def test_forward_rate_invalid(self):
        curve = self._make_curve()
        with pytest.raises(ValueError):
            curve.forward_rate(5.0, 2.0)

    def test_discount_factor(self):
        curve = self._make_curve()
        df = curve.discount_factor(1.0)
        assert 0 < df < 1

    def test_is_inverted(self):
        curve = self._make_curve()
        # Our curve is inverted (short rate 4.5% > long rate 3.7%)
        assert curve.is_inverted() is True

    def test_normal_curve_not_inverted(self):
        from src.fixed_income.yield_curve import YieldCurve
        curve = YieldCurve([1, 5, 10, 30], [0.02, 0.03, 0.035, 0.04])
        assert curve.is_inverted() is False

    def test_mismatched_lengths_raises(self):
        from src.fixed_income.yield_curve import YieldCurve
        with pytest.raises(ValueError):
            YieldCurve([1, 2, 5], [0.02, 0.03])

    def test_too_few_points_raises(self):
        from src.fixed_income.yield_curve import YieldCurve
        with pytest.raises(ValueError):
            YieldCurve([1], [0.02])


# ══════════════════════════════════════════════════════════════════
# DeploymentConfig (additional edge cases)
# ══════════════════════════════════════════════════════════════════

class TestDeploymentConfigEdgeCases:
    def test_invalid_workers(self):
        from src.deploy import DeploymentConfig
        config = DeploymentConfig(workers=0)
        assert config.validate() is False

    def test_invalid_log_level(self):
        from src.deploy import DeploymentConfig
        config = DeploymentConfig(log_level="verbose")
        assert config.validate() is False

    def test_valid_debug_level(self):
        from src.deploy import DeploymentConfig
        config = DeploymentConfig(log_level="debug")
        assert config.validate() is True

    def test_env_string_content(self):
        from src.deploy import DeploymentConfig
        config = DeploymentConfig(port=9999, host="127.0.0.1")
        env_str = config.to_env_string()
        assert "FINCLAW_PORT=9999" in env_str
        assert "FINCLAW_HOST=127.0.0.1" in env_str

    def test_from_env_defaults(self):
        from src.deploy import DeploymentConfig
        # Clean env
        for key in ["FINCLAW_PORT", "FINCLAW_WORKERS"]:
            os.environ.pop(key, None)
        config = DeploymentConfig.from_env()
        assert config.port == 8080
        assert config.workers == 1
