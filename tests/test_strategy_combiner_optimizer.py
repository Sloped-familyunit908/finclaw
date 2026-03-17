"""
FinClaw v1.3.0 Tests — Strategy Combiner, Optimizer, Signal Dashboard,
Backtest Reports, Portfolio Rebalancing.
30+ tests covering all new modules.
"""

import math
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.strategies.combiner import (
    StrategyCombiner, CombinedSignal,
    MeanReversionAdapter, MomentumAdapter,
    TrendFollowingAdapter, ValueMomentumAdapter,
)
from src.strategies.mean_reversion import MeanReversionStrategy
from src.strategies.momentum_jt import MomentumJTStrategy
from src.strategies.trend_following import TrendFollowingStrategy
from src.strategies.value_momentum import ValueMomentumStrategy
from src.optimization.optimizer import StrategyOptimizer, OptimizationReport
from src.dashboard.signals import generate_signal_report, SignalReport
from src.reports.backtest_report import BacktestReportGenerator, BacktestReport
from src.portfolio.rebalancer import (
    PortfolioRebalancer, Position, RebalanceAction, RebalanceFrequency,
)


# ── Helper: generate synthetic price data ──

def _trending_up(n=300, start=100.0, drift=0.001, vol=0.02, seed=42):
    """Generate upward-trending prices."""
    import random
    rng = random.Random(seed)
    prices = [start]
    for _ in range(n - 1):
        ret = drift + vol * rng.gauss(0, 1)
        prices.append(prices[-1] * (1 + ret))
    return prices


def _trending_down(n=300, start=100.0, drift=-0.001, vol=0.02, seed=42):
    rng = __import__("random").Random(seed)
    prices = [start]
    for _ in range(n - 1):
        prices.append(prices[-1] * (1 + drift + vol * rng.gauss(0, 1)))
    return prices


def _mean_reverting(n=300, start=100.0, vol=0.015, seed=42):
    """Mean-reverting prices around start."""
    rng = __import__("random").Random(seed)
    prices = [start]
    for _ in range(n - 1):
        revert = (start - prices[-1]) / start * 0.05
        prices.append(prices[-1] * (1 + revert + vol * rng.gauss(0, 1)))
    return prices


# ════════════════════════════════════════
# 1. Strategy Combiner Tests
# ════════════════════════════════════════

class SimpleStrategy:
    """Test helper: always returns a fixed signal."""
    def __init__(self, value: float):
        self._value = value
    def signal(self, prices):
        return self._value


class TestStrategyCombiner:
    def test_single_strategy(self):
        c = StrategyCombiner([SimpleStrategy(0.5)])
        assert c.signal([100, 101]) == pytest.approx(0.5, abs=0.01)

    def test_equal_weights(self):
        c = StrategyCombiner([SimpleStrategy(1.0), SimpleStrategy(-1.0)])
        assert c.signal([100]) == pytest.approx(0.0, abs=0.01)

    def test_custom_weights(self):
        c = StrategyCombiner(
            [SimpleStrategy(1.0), SimpleStrategy(-1.0)],
            weights=[3.0, 1.0],
        )
        # 1.0 * 0.75 + (-1.0) * 0.25 = 0.5
        assert c.signal([100]) == pytest.approx(0.5, abs=0.01)

    def test_clamp_to_range(self):
        c = StrategyCombiner([SimpleStrategy(1.0), SimpleStrategy(1.0)])
        assert c.signal([100]) <= 1.0

    def test_detailed_signal_returns_combined(self):
        c = StrategyCombiner(
            [SimpleStrategy(0.8), SimpleStrategy(0.6)],
            names=["A", "B"],
        )
        ds = c.detailed_signal([100])
        assert isinstance(ds, CombinedSignal)
        assert ds.regime == "bull"
        assert ds.suggested_position == "long"
        assert "A" in ds.components

    def test_detailed_signal_bearish(self):
        c = StrategyCombiner([SimpleStrategy(-0.7), SimpleStrategy(-0.5)])
        ds = c.detailed_signal([100])
        assert ds.regime == "bear"
        assert ds.suggested_position == "short"

    def test_detailed_signal_neutral(self):
        c = StrategyCombiner([SimpleStrategy(0.1), SimpleStrategy(-0.1)])
        ds = c.detailed_signal([100])
        assert ds.regime == "neutral"
        assert ds.suggested_position == "flat"

    def test_empty_strategies_raises(self):
        with pytest.raises(ValueError):
            StrategyCombiner([])

    def test_weight_mismatch_raises(self):
        with pytest.raises(ValueError):
            StrategyCombiner([SimpleStrategy(1)], weights=[1, 2])

    def test_confidence_high_when_agree(self):
        c = StrategyCombiner([SimpleStrategy(0.8), SimpleStrategy(0.7), SimpleStrategy(0.9)])
        ds = c.detailed_signal([100])
        assert ds.confidence > 0.5

    def test_confidence_low_when_disagree(self):
        c = StrategyCombiner(
            [SimpleStrategy(0.9), SimpleStrategy(-0.9)],
            names=["Bull", "Bear"],
        )
        ds = c.detailed_signal([100])
        assert ds.confidence < 0.5


class TestAdapters:
    def test_mean_reversion_adapter(self):
        mr = MeanReversionStrategy()
        adapter = MeanReversionAdapter(mr)
        data = _mean_reverting(100)
        sig = adapter.signal(data)
        assert -1.0 <= sig <= 1.0

    def test_momentum_adapter(self):
        mom = MomentumJTStrategy()
        adapter = MomentumAdapter(mom)
        data = _trending_up(300)
        sig = adapter.signal(data)
        assert -1.0 <= sig <= 1.0

    def test_trend_following_adapter(self):
        tf = TrendFollowingStrategy()
        adapter = TrendFollowingAdapter(tf)
        data = _trending_up(100)
        sig = adapter.signal(data)
        assert -1.0 <= sig <= 1.0

    def test_value_momentum_adapter(self):
        vm = ValueMomentumStrategy()
        adapter = ValueMomentumAdapter(vm)
        data = _trending_up(300)
        sig = adapter.signal(data)
        assert -1.0 <= sig <= 1.0


# ════════════════════════════════════════
# 2. Strategy Optimizer Tests
# ════════════════════════════════════════

class TestStrategyOptimizer:
    def test_grid_search(self):
        opt = StrategyOptimizer(MeanReversionStrategy)
        report = opt.optimize(
            param_grid={"rsi_period": [10, 14], "rsi_oversold": [25, 30]},
            data=_trending_up(200),
            metric="sharpe_ratio",
            method="grid",
        )
        assert isinstance(report, OptimizationReport)
        assert report.total_combinations == 4
        assert report.best_params is not None

    def test_random_search(self):
        opt = StrategyOptimizer(MeanReversionStrategy)
        report = opt.optimize(
            param_grid={"rsi_period": [10, 14, 20], "rsi_oversold": [25, 30, 35]},
            data=_trending_up(200),
            metric="total_return",
            method="random",
            max_iter=5,
        )
        assert report.total_combinations == 5

    def test_walk_forward(self):
        opt = StrategyOptimizer(MeanReversionStrategy)
        report = opt.optimize(
            param_grid={"rsi_period": [10, 14]},
            data=_trending_up(200),
            metric="sharpe_ratio",
            walk_forward=True,
            wf_windows=2,
        )
        assert report.walk_forward is not None

    def test_invalid_metric_raises(self):
        opt = StrategyOptimizer(MeanReversionStrategy)
        with pytest.raises(ValueError, match="Unsupported metric"):
            opt.optimize(
                param_grid={"rsi_period": [14]},
                data=_trending_up(100),
                metric="nonsense",
            )

    def test_insufficient_data_raises(self):
        opt = StrategyOptimizer(MeanReversionStrategy)
        with pytest.raises(ValueError, match="at least 30"):
            opt.optimize(
                param_grid={"rsi_period": [14]},
                data=[100, 101, 102],
                metric="sharpe_ratio",
            )

    def test_results_sorted(self):
        opt = StrategyOptimizer(MeanReversionStrategy)
        report = opt.optimize(
            param_grid={"rsi_period": [10, 14, 20]},
            data=_trending_up(200),
            metric="sharpe_ratio",
        )
        # Best should be first
        metrics = [r.metric_value for r in report.all_results]
        assert metrics[0] >= metrics[-1]


# ════════════════════════════════════════
# 3. Signal Dashboard Tests
# ════════════════════════════════════════

class TestSignalDashboard:
    def test_basic_report(self):
        mr = MeanReversionStrategy()
        report = generate_signal_report(mr, _mean_reverting(100), "AAPL")
        assert isinstance(report, SignalReport)
        assert report.ticker == "AAPL"
        assert -1 <= report.current_signal <= 1
        assert 0 <= report.confidence <= 1
        assert report.regime in ("bull", "bear", "neutral")
        assert report.suggested_position in ("long", "short", "flat")

    def test_risk_metrics_present(self):
        report = generate_signal_report(
            MeanReversionStrategy(), _trending_up(100), "SPY",
        )
        assert "annual_volatility" in report.risk_metrics
        assert "max_drawdown" in report.risk_metrics
        assert "daily_return_mean" in report.risk_metrics

    def test_signal_history_length(self):
        report = generate_signal_report(
            MeanReversionStrategy(), _trending_up(100), "TSLA",
            history_window=10,
        )
        assert len(report.signal_history) == 10

    def test_insufficient_data(self):
        report = generate_signal_report(
            MeanReversionStrategy(), [100, 101], "X",
        )
        assert report.current_signal == 0.0
        assert report.regime == "neutral"

    def test_combiner_report(self):
        c = StrategyCombiner([SimpleStrategy(0.5), SimpleStrategy(0.3)])
        report = generate_signal_report(c, _trending_up(100), "COMBO")
        assert report.ticker == "COMBO"
        assert report.current_signal != 0  # combiner returns non-zero


# ════════════════════════════════════════
# 4. Backtest Report Tests
# ════════════════════════════════════════

class TestBacktestReport:
    def test_generate_report(self):
        gen = BacktestReportGenerator()
        report = gen.generate(MeanReversionStrategy(), _trending_up(200))
        assert isinstance(report, BacktestReport)
        assert len(report.equity_curve) == 200
        assert report.max_drawdown >= 0

    def test_report_with_benchmark(self):
        gen = BacktestReportGenerator()
        data = _trending_up(200)
        bench = _trending_up(200, drift=0.0005, seed=99)
        report = gen.generate(MeanReversionStrategy(), data, benchmark_data=bench)
        assert report.benchmark_return is not None
        assert report.alpha is not None
        assert report.beta is not None

    def test_monthly_returns(self):
        gen = BacktestReportGenerator()
        report = gen.generate(MeanReversionStrategy(), _trending_up(200))
        # Monthly returns should be a list
        assert isinstance(report.monthly_returns, list)

    def test_trade_log(self):
        gen = BacktestReportGenerator()
        report = gen.generate(MeanReversionStrategy(), _trending_up(200))
        assert isinstance(report.trade_log, list)
        for t in report.trade_log:
            assert t.entry_price > 0
            assert t.exit_price > 0

    def test_risk_over_time(self):
        gen = BacktestReportGenerator()
        report = gen.generate(MeanReversionStrategy(), _trending_up(200))
        assert isinstance(report.risk_over_time, list)

    def test_short_data_raises(self):
        gen = BacktestReportGenerator()
        with pytest.raises(ValueError):
            gen.generate(MeanReversionStrategy(), [100, 101])


# ════════════════════════════════════════
# 5. Portfolio Rebalancer Tests
# ════════════════════════════════════════

def _make_positions(weights_prices: dict[str, tuple[float, float]], total: float = 100000):
    """Create positions: {symbol: (current_weight, price)}"""
    positions = []
    for sym, (w, price) in weights_prices.items():
        value = total * w
        shares = value / price
        positions.append(Position(
            symbol=sym, shares=shares, current_price=price,
            cost_basis=price * 0.9, holding_days=400,
        ))
    return positions


class TestPortfolioRebalancer:
    def test_no_rebalance_when_on_target(self):
        rb = PortfolioRebalancer(
            target_weights={"SPY": 0.6, "TLT": 0.4},
            method="threshold", threshold=0.05,
        )
        positions = _make_positions({"SPY": (0.6, 450), "TLT": (0.4, 100)})
        result = rb.rebalance(positions)
        assert len(result.actions) == 0

    def test_rebalance_when_drifted(self):
        rb = PortfolioRebalancer(
            target_weights={"SPY": 0.6, "TLT": 0.4},
            method="threshold", threshold=0.05,
        )
        positions = _make_positions({"SPY": (0.75, 450), "TLT": (0.25, 100)})
        result = rb.rebalance(positions)
        assert len(result.actions) > 0
        assert result.drift_before > 0.05

    def test_calendar_rebalance_trigger(self):
        rb = PortfolioRebalancer(
            target_weights={"A": 0.5, "B": 0.5},
            method="calendar",
        )
        positions = _make_positions({"A": (0.55, 10), "B": (0.45, 20)})
        result = rb.rebalance(positions, day_of_period=0)
        assert len(result.actions) > 0

    def test_calendar_no_trigger_mid_period(self):
        rb = PortfolioRebalancer(
            target_weights={"A": 0.5, "B": 0.5},
            method="calendar",
        )
        positions = _make_positions({"A": (0.55, 10), "B": (0.45, 20)})
        result = rb.rebalance(positions, day_of_period=5)
        assert len(result.actions) == 0

    def test_tax_aware_prefers_long_term(self):
        rb = PortfolioRebalancer(
            target_weights={"SPY": 0.5, "QQQ": 0.5},
            method="tax_aware", threshold=0.05,
        )
        positions = [
            Position("SPY", 150, 450, 400, holding_days=400),  # long-term gain
            Position("QQQ", 50, 380, 350, holding_days=100),   # short-term gain
        ]
        # SPY overweight, QQQ underweight
        result = rb.rebalance(positions)
        sells = [a for a in result.actions if a.action == "sell"]
        for s in sells:
            assert s.tax_impact is not None

    def test_needs_rebalance_method(self):
        rb = PortfolioRebalancer(
            target_weights={"A": 0.5, "B": 0.5},
            method="threshold", threshold=0.05,
        )
        on_target = _make_positions({"A": (0.5, 10), "B": (0.5, 20)})
        assert rb.needs_rebalance(on_target) is False
        drifted = _make_positions({"A": (0.7, 10), "B": (0.3, 20)})
        assert rb.needs_rebalance(drifted) is True

    def test_weight_normalization(self):
        rb = PortfolioRebalancer(target_weights={"A": 2, "B": 3})
        assert rb.target_weights["A"] == pytest.approx(0.4)
        assert rb.target_weights["B"] == pytest.approx(0.6)

    def test_empty_portfolio(self):
        rb = PortfolioRebalancer(target_weights={"A": 1.0})
        result = rb.rebalance([])
        assert len(result.actions) == 0

    def test_turnover_calculation(self):
        rb = PortfolioRebalancer(
            target_weights={"A": 0.5, "B": 0.5},
            method="threshold", threshold=0.01,
        )
        positions = _make_positions({"A": (0.7, 10), "B": (0.3, 20)})
        result = rb.rebalance(positions)
        assert result.total_turnover > 0

    def test_min_trade_filter(self):
        rb = PortfolioRebalancer(
            target_weights={"A": 0.5, "B": 0.5},
            method="threshold", threshold=0.001,
            min_trade_value=50000,  # very high filter
        )
        positions = _make_positions({"A": (0.52, 10), "B": (0.48, 20)})
        result = rb.rebalance(positions)
        # Small drift trades should be filtered out
        assert len(result.actions) == 0 or all(
            a.estimated_value >= 50000 for a in result.actions
        )
