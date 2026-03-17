"""
FinClaw v1.7.0 Tests — Event-Driven Architecture & Advanced Analytics
30+ tests covering EventBus, OMS, Execution Analytics, Correlation, Scenarios.
"""

import math
import time
import pytest


# ============================================================
# EventBus Tests
# ============================================================

class TestEventBus:
    def _make_bus(self):
        from src.events.event_bus import EventBus
        return EventBus()

    def test_subscribe_and_publish(self):
        bus = self._make_bus()
        received = []
        bus.subscribe("test", lambda e: received.append(e.data))
        bus.publish("test", {"val": 1})
        assert len(received) == 1
        assert received[0]["val"] == 1

    def test_multiple_handlers(self):
        bus = self._make_bus()
        a, b = [], []
        bus.subscribe("x", lambda e: a.append(1))
        bus.subscribe("x", lambda e: b.append(2))
        bus.publish("x", {})
        assert len(a) == 1 and len(b) == 1

    def test_unsubscribe(self):
        bus = self._make_bus()
        received = []
        handler = lambda e: received.append(1)
        bus.subscribe("x", handler)
        assert bus.unsubscribe("x", handler) is True
        bus.publish("x", {})
        assert len(received) == 0

    def test_unsubscribe_missing(self):
        bus = self._make_bus()
        assert bus.unsubscribe("x", lambda e: None) is False

    def test_wildcard_subscription(self):
        bus = self._make_bus()
        received = []
        bus.subscribe("*", lambda e: received.append(e.event_type))
        bus.publish("a", {})
        bus.publish("b", {})
        assert received == ["a", "b"]

    def test_event_history(self):
        bus = self._make_bus()
        bus.publish("a", {"n": 1})
        bus.publish("b", {"n": 2})
        bus.publish("a", {"n": 3})
        assert len(bus.get_history()) == 3
        assert len(bus.get_history("a")) == 2

    def test_history_limit(self):
        from src.events.event_bus import EventBus
        bus = EventBus(max_history=5)
        for i in range(10):
            bus.publish("x", {"i": i})
        assert len(bus.get_history()) == 5

    def test_handler_error_doesnt_break_others(self):
        bus = self._make_bus()
        received = []
        bus.subscribe("x", lambda e: (_ for _ in ()).throw(ValueError("boom")))
        bus.subscribe("x", lambda e: received.append(1))
        # The bad handler raises but the second should still run
        bus.publish("x", {})
        # Actually the lambda trick won't work; use a real function
        # Re-test with proper error handler
        bus.clear()
        received.clear()
        def bad(e): raise ValueError("boom")
        def good(e): received.append(1)
        bus.subscribe("x", bad)
        bus.subscribe("x", good)
        bus.publish("x", {})
        assert len(received) == 1

    def test_clear(self):
        bus = self._make_bus()
        bus.subscribe("x", lambda e: None)
        bus.publish("x", {})
        bus.clear()
        assert bus.handler_count == 0
        assert len(bus.get_history()) == 0

    def test_event_source(self):
        bus = self._make_bus()
        event = bus.publish("x", {"a": 1}, source="test_module")
        assert event.source == "test_module"


# ============================================================
# OMS Tests
# ============================================================

class TestOrderManager:
    def _make_oms(self, bus=None):
        from src.trading.oms import OrderManager
        return OrderManager(event_bus=bus)

    def _order(self, **kw):
        from src.trading.oms import Order
        defaults = dict(ticker="AAPL", side="buy", order_type="market", quantity=10, limit_price=150.0)
        defaults.update(kw)
        return Order(**defaults)

    def test_submit_market_order(self):
        oms = self._make_oms()
        result = oms.submit_order(self._order())
        assert result.status == "filled"
        assert result.filled_quantity == 10

    def test_reject_zero_quantity(self):
        oms = self._make_oms()
        result = oms.submit_order(self._order(quantity=0))
        assert result.status == "rejected"

    def test_reject_limit_without_price(self):
        oms = self._make_oms()
        result = oms.submit_order(self._order(order_type="limit", limit_price=None))
        assert result.status == "rejected"

    def test_reject_stop_without_price(self):
        oms = self._make_oms()
        result = oms.submit_order(self._order(order_type="stop", stop_price=None))
        assert result.status == "rejected"

    def test_limit_order_goes_open(self):
        oms = self._make_oms()
        result = oms.submit_order(self._order(order_type="limit", limit_price=145.0))
        assert result.status == "open"

    def test_cancel_order(self):
        oms = self._make_oms()
        result = oms.submit_order(self._order(order_type="limit", limit_price=145.0))
        assert oms.cancel_order(result.order_id) is True
        assert len(oms.get_open_orders()) == 0

    def test_cancel_nonexistent(self):
        oms = self._make_oms()
        assert oms.cancel_order("fake-id") is False

    def test_order_history(self):
        oms = self._make_oms()
        oms.submit_order(self._order())
        oms.submit_order(self._order(ticker="MSFT"))
        assert len(oms.get_order_history()) == 2

    def test_event_bus_integration(self):
        from src.events.event_bus import EventBus
        bus = EventBus()
        trades = []
        bus.subscribe("trade_executed", lambda e: trades.append(e.data))
        oms = self._make_oms(bus=bus)
        oms.submit_order(self._order())
        assert len(trades) == 1
        assert trades[0]["ticker"] == "AAPL"

    def test_check_limit_buy_trigger(self):
        oms = self._make_oms()
        oms.submit_order(self._order(order_type="limit", limit_price=145.0))
        results = oms.check_stops_and_limits({"AAPL": 144.0})
        assert len(results) == 1 and results[0].status == "filled"

    def test_check_stop_sell_trigger(self):
        oms = self._make_oms()
        oms.submit_order(self._order(side="sell", order_type="stop", stop_price=140.0))
        results = oms.check_stops_and_limits({"AAPL": 139.0})
        assert len(results) == 1

    def test_check_no_trigger(self):
        oms = self._make_oms()
        oms.submit_order(self._order(order_type="limit", limit_price=130.0))
        results = oms.check_stops_and_limits({"AAPL": 150.0})
        assert len(results) == 0


# ============================================================
# Execution Analytics Tests
# ============================================================

class TestExecutionAnalyzer:
    def _make(self):
        from src.analytics.execution import ExecutionAnalyzer
        return ExecutionAnalyzer()

    def test_no_slippage(self):
        ea = self._make()
        r = ea.analyze_fill("O1", "AAPL", "buy", 150.0, 150.0, 100)
        assert r.slippage_bps == 0.0

    def test_buy_positive_slippage(self):
        ea = self._make()
        r = ea.analyze_fill("O1", "AAPL", "buy", 150.0, 150.15, 100)
        assert r.slippage_bps > 0  # paid more than expected

    def test_sell_positive_slippage(self):
        ea = self._make()
        r = ea.analyze_fill("O1", "AAPL", "sell", 150.0, 149.85, 100)
        assert r.slippage_bps > 0  # received less than expected

    def test_vwap_comparison(self):
        ea = self._make()
        r = ea.analyze_fill("O1", "AAPL", "buy", 150.0, 150.0, 100, vwap=149.5)
        assert r.vwap_diff_bps > 0

    def test_execution_delay(self):
        ea = self._make()
        r = ea.analyze_fill("O1", "AAPL", "buy", 150.0, 150.0, 100,
                            signal_time_ms=1000, fill_time_ms=1250)
        assert r.execution_delay_ms == 250

    def test_summary(self):
        ea = self._make()
        ea.analyze_fill("O1", "AAPL", "buy", 150.0, 150.15, 100)
        ea.analyze_fill("O2", "MSFT", "sell", 300.0, 299.7, 50)
        s = ea.get_summary()
        assert s["n_trades"] == 2
        assert s["avg_slippage_bps"] > 0

    def test_empty_summary(self):
        ea = self._make()
        assert ea.get_summary()["n_trades"] == 0


# ============================================================
# Correlation Analysis Tests
# ============================================================

class TestCorrelationAnalyzer:
    def _make(self):
        from src.analytics.correlation import CorrelationAnalyzer
        return CorrelationAnalyzer()

    def test_perfect_correlation(self):
        ca = self._make()
        x = [0.01 * i for i in range(100)]
        assert abs(ca.pearson(x, x) - 1.0) < 1e-6

    def test_negative_correlation(self):
        ca = self._make()
        x = [0.01 * i for i in range(100)]
        y = [-v for v in x]
        assert abs(ca.pearson(x, y) - (-1.0)) < 1e-6

    def test_correlation_matrix_diagonal(self):
        ca = self._make()
        returns = {"A": [0.01, -0.02, 0.03], "B": [0.02, -0.01, 0.01]}
        m = ca.correlation_matrix(returns)
        assert m["A"]["A"] == 1.0
        assert m["B"]["B"] == 1.0

    def test_correlation_matrix_symmetric(self):
        ca = self._make()
        import random; rng = random.Random(42)
        returns = {t: [rng.gauss(0, 0.01) for _ in range(50)] for t in ["A", "B", "C"]}
        m = ca.correlation_matrix(returns)
        assert abs(m["A"]["B"] - m["B"]["A"]) < 1e-10

    def test_rolling_correlation_length(self):
        ca = self._make()
        x = [0.01 * i for i in range(100)]
        y = [0.02 * i for i in range(100)]
        rc = ca.rolling_correlation(x, y, window=20)
        assert len(rc) == 100
        assert math.isnan(rc[0])
        assert not math.isnan(rc[19])

    def test_hierarchical_cluster(self):
        ca = self._make()
        import random; rng = random.Random(7)
        base = [rng.gauss(0, 0.01) for _ in range(50)]
        returns = {
            "A": base,
            "B": [b + rng.gauss(0, 0.001) for b in base],  # highly correlated with A
            "C": [rng.gauss(0, 0.01) for _ in range(50)],  # independent
        }
        merges = ca.hierarchical_cluster(returns)
        assert len(merges) == 2  # 3 items → 2 merges
        # First merge should involve A and B (most correlated)
        first = merges[0]
        assert ("A" in first[0] or "A" in first[1]) and ("B" in first[0] or "B" in first[1])

    def test_diversification_ratio_identical(self):
        ca = self._make()
        data = [0.01, -0.02, 0.03, -0.01, 0.02]
        returns = {"A": data, "B": data}
        dr = ca.diversification_ratio(returns, {"A": 0.5, "B": 0.5})
        assert abs(dr - 1.0) < 0.1  # identical assets → ~1

    def test_diversification_ratio_uncorrelated(self):
        ca = self._make()
        import random; rng = random.Random(99)
        returns = {
            "A": [rng.gauss(0, 0.02) for _ in range(500)],
            "B": [rng.gauss(0, 0.02) for _ in range(500)],
        }
        dr = ca.diversification_ratio(returns, {"A": 0.5, "B": 0.5})
        assert dr > 1.1  # uncorrelated → diversification benefit


# ============================================================
# Scenario Generator Tests
# ============================================================

class TestScenarioGenerator:
    def _make(self, seed=42):
        from src.simulation.scenarios import ScenarioGenerator
        return ScenarioGenerator(seed=seed)

    def test_list_scenarios(self):
        sg = self._make()
        names = sg.list_scenarios()
        assert "2008_financial_crisis" in names
        assert "covid_2020" in names

    def test_generate_2008(self):
        sg = self._make()
        r = sg.generate("2008_financial_crisis")
        assert r.max_drawdown < -0.2  # should be severe
        assert len(r.daily_values) > 100

    def test_generate_covid(self):
        sg = self._make()
        r = sg.generate("covid_2020")
        assert r.max_drawdown < -0.1

    def test_generate_unknown_raises(self):
        sg = self._make()
        with pytest.raises(ValueError):
            sg.generate("alien_invasion")

    def test_custom_scenario(self):
        sg = self._make()
        r = sg.generate_custom(drawdown=-0.30, duration_days=60, recovery_days=120)
        assert r.max_drawdown < -0.1
        assert len(r.daily_values) == 60 + 120 + 1

    def test_portfolio_value_applied(self):
        sg = self._make()
        r = sg.generate("flash_crash_2010", portfolio_value=50000)
        assert r.portfolio_start == 50000
        assert r.daily_values[0] == 50000

    def test_deterministic_with_seed(self):
        r1 = self._make(seed=7).generate("covid_2020")
        r2 = self._make(seed=7).generate("covid_2020")
        assert r1.daily_values == r2.daily_values
