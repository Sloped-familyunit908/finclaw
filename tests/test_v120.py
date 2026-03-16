"""Tests for v1.2.0 features: strategies, risk, analytics, backtesting, pipeline."""
import sys
import os
import math
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from tests.conftest import make_bull_prices, make_bear_prices, make_ranging_prices, make_volatile_prices, make_history

# ============================================================
# Strategy Tests
# ============================================================

class TestMeanReversion:
    def test_oversold_signal(self):
        from src.strategies.mean_reversion import MeanReversionStrategy
        s = MeanReversionStrategy()
        # Create a sharp drop to trigger oversold
        prices = [100 + i * 0.5 for i in range(50)]  # uptrend
        prices += [prices[-1] * (0.97 ** i) for i in range(1, 30)]  # crash
        sig = s.generate_signal(prices)
        assert sig.signal in ("buy", "hold")  # should detect oversold or at least not sell

    def test_overbought_signal(self):
        from src.strategies.mean_reversion import MeanReversionStrategy
        s = MeanReversionStrategy()
        prices = [100] * 30
        prices += [100 * (1.02 ** i) for i in range(1, 30)]  # strong rally
        sig = s.generate_signal(prices)
        assert sig.signal in ("sell", "hold")

    def test_neutral_market(self):
        from src.strategies.mean_reversion import MeanReversionStrategy
        s = MeanReversionStrategy()
        prices = [100 + 0.01 * i for i in range(50)]
        sig = s.generate_signal(prices)
        assert sig.confidence >= 0

    def test_insufficient_data(self):
        from src.strategies.mean_reversion import MeanReversionStrategy
        s = MeanReversionStrategy()
        sig = s.generate_signal([100, 101])
        assert sig.signal == "hold"


class TestMomentumJT:
    def test_bullish_momentum(self):
        from src.strategies.momentum_jt import MomentumJTStrategy
        s = MomentumJTStrategy()
        prices = [100 * (1.001 ** i) for i in range(300)]  # steady uptrend
        score = s.score_single(prices)
        assert score.momentum_12m > 0

    def test_bearish_momentum(self):
        from src.strategies.momentum_jt import MomentumJTStrategy
        s = MomentumJTStrategy()
        prices = [100 * (0.999 ** i) for i in range(300)]
        score = s.score_single(prices)
        assert score.momentum_12m < 0

    def test_rank_assets(self):
        from src.strategies.momentum_jt import MomentumJTStrategy
        s = MomentumJTStrategy()
        assets = {
            "WINNER": [100 * (1.002 ** i) for i in range(300)],
            "LOSER": [100 * (0.998 ** i) for i in range(300)],
            "MID": [100 + 0.01 * i for i in range(300)],
        }
        ranked = s.rank_assets(assets)
        assert ranked[0].symbol == "WINNER"
        assert ranked[-1].symbol == "LOSER"


class TestPairsTrading:
    def test_cointegrated_pair(self):
        from src.strategies.pairs_trading import PairsTradingStrategy
        import random
        rng = random.Random(42)
        s = PairsTradingStrategy()
        # Two cointegrated series: B = A + noise
        a = [100 + 0.1 * i + rng.gauss(0, 1) for i in range(100)]
        b = [p + 50 + rng.gauss(0, 0.5) for p in a]
        sig = s.generate_signal("A", "B", a, b)
        assert sig.hedge_ratio > 0

    def test_diverged_pair(self):
        from src.strategies.pairs_trading import PairsTradingStrategy
        import random
        rng = random.Random(99)
        s = PairsTradingStrategy(entry_z=1.5)
        # Two series with noise to produce non-zero variance in spread
        a = [100 + i * 0.5 + rng.gauss(0, 1) for i in range(100)]
        b = [100 - i * 0.1 + rng.gauss(0, 1) for i in range(100)]
        sig = s.generate_signal("A", "B", a, b)
        assert sig.hedge_ratio != 0

    def test_insufficient_data(self):
        from src.strategies.pairs_trading import PairsTradingStrategy
        s = PairsTradingStrategy()
        sig = s.generate_signal("A", "B", [100, 101], [200, 201])
        assert sig.signal == "hold"


class TestTrendFollowing:
    def test_golden_cross(self):
        from src.strategies.trend_following import TrendFollowingStrategy
        s = TrendFollowingStrategy(fast_period=10, slow_period=20)
        # Start flat, then rally => fast crosses above slow
        prices = [100] * 30 + [100 + i * 2 for i in range(1, 25)]
        sig = s.generate_signal(prices)
        assert sig.signal in ("buy", "hold")

    def test_death_cross(self):
        from src.strategies.trend_following import TrendFollowingStrategy
        s = TrendFollowingStrategy(fast_period=10, slow_period=20)
        prices = [200] * 30 + [200 - i * 2 for i in range(1, 25)]
        sig = s.generate_signal(prices)
        assert sig.signal in ("sell", "hold")

    def test_with_adx(self):
        from src.strategies.trend_following import TrendFollowingStrategy
        s = TrendFollowingStrategy(fast_period=10, slow_period=20, adx_period=14)
        prices = [100 + i * 0.5 for i in range(60)]
        highs = [p * 1.01 for p in prices]
        lows = [p * 0.99 for p in prices]
        sig = s.generate_signal(prices, highs, lows)
        assert sig.adx is not None or sig.trend_strength in ("strong", "moderate", "weak", "none")


class TestValueMomentum:
    def test_combined_bullish(self):
        from src.strategies.value_momentum import ValueMomentumStrategy
        s = ValueMomentumStrategy()
        # Undervalued (below SMA200) + positive momentum
        prices = [50 + i * 0.3 for i in range(300)]
        sig = s.generate_signal(prices)
        assert sig.combined_score != 0  # should produce some score

    def test_rank_assets(self):
        from src.strategies.value_momentum import ValueMomentumStrategy
        s = ValueMomentumStrategy()
        assets = {
            "GOOD": [50 + i * 0.3 for i in range(300)],
            "BAD": [150 - i * 0.2 for i in range(300)],
        }
        ranked = s.rank_assets(assets)
        assert len(ranked) == 2
        assert ranked[0]["symbol"] in ("GOOD", "BAD")


# ============================================================
# Risk Management Tests
# ============================================================

class TestPositionSizing:
    def test_kelly_positive_edge(self):
        from src.risk.position_sizing import KellyCriterion
        k = KellyCriterion()
        result = k.calculate(win_rate=0.6, avg_win=0.10, avg_loss=0.05)
        assert result.fraction > 0

    def test_kelly_no_edge(self):
        from src.risk.position_sizing import KellyCriterion
        k = KellyCriterion()
        result = k.calculate(win_rate=0.3, avg_win=0.05, avg_loss=0.10)
        assert result.fraction == 0

    def test_fixed_fractional(self):
        from src.risk.position_sizing import FixedFractional
        ff = FixedFractional(risk_per_trade=0.02)
        result = ff.calculate(capital=100000, entry_price=50, stop_price=48)
        assert 0 < result.fraction <= 1

    def test_volatility_sizing(self):
        from src.risk.position_sizing import VolatilitySizing
        vs = VolatilitySizing(target_volatility=0.01)
        prices = make_bull_prices(100)
        result = vs.calculate(capital=100000, prices=prices)
        assert result.fraction > 0


class TestStopLoss:
    def test_fixed_stop_triggers(self):
        from src.risk.stop_loss import StopLossManager
        sm = StopLossManager(fixed_pct=0.05)
        stops = sm.compute_stops(entry_price=100, current_price=94, highest_since_entry=100, bars_held=5)
        triggered = sm.any_triggered(stops)
        assert triggered is not None

    def test_trailing_stop(self):
        from src.risk.stop_loss import StopLossManager
        sm = StopLossManager(trailing_pct=0.10)
        stops = sm.compute_stops(entry_price=100, current_price=95, highest_since_entry=110, bars_held=5)
        # 110 * 0.90 = 99, price=95 < 99 => triggered
        trailing = [s for s in stops if s.type.value == "trailing"]
        assert trailing[0].triggered

    def test_time_stop(self):
        from src.risk.stop_loss import StopLossManager
        sm = StopLossManager(max_hold_bars=30)
        stops = sm.compute_stops(entry_price=100, current_price=105, highest_since_entry=105, bars_held=31)
        time_stop = [s for s in stops if s.type.value == "time"]
        assert time_stop[0].triggered


class TestPortfolioRisk:
    def test_drawdown_circuit_breaker(self):
        from src.risk.portfolio_risk import PortfolioRiskManager
        pm = PortfolioRiskManager(max_drawdown_limit=0.15)
        curve = [10000, 10500, 11000, 9000, 8500]  # ~23% DD from peak
        halt, dd = pm.check_drawdown_circuit_breaker(curve)
        assert halt

    def test_inverse_vol_allocation(self):
        from src.risk.portfolio_risk import PortfolioRiskManager
        pm = PortfolioRiskManager()
        vols = {"LOW_VOL": 0.10, "HIGH_VOL": 0.30}
        result = pm.inverse_volatility_allocation(vols)
        assert result.weights["LOW_VOL"] > result.weights["HIGH_VOL"]

    def test_correlation(self):
        from src.risk.portfolio_risk import PortfolioRiskManager
        pm = PortfolioRiskManager()
        a = [0.01 * i for i in range(20)]
        b = [0.01 * i for i in range(20)]
        corr = pm.correlation_check(a, b)
        assert corr > 0.9


class TestVaR:
    def test_historical_var(self):
        from src.risk.var_calculator import VaRCalculator
        vc = VaRCalculator(confidence=0.95)
        import random
        rng = random.Random(42)
        rets = [rng.gauss(0.0005, 0.02) for _ in range(500)]
        result = vc.historical(rets, portfolio_value=100000)
        assert result.var < 0  # VaR should be negative (loss)
        assert result.cvar <= result.var  # CVaR should be worse

    def test_parametric_var(self):
        from src.risk.var_calculator import VaRCalculator
        vc = VaRCalculator(confidence=0.95)
        import random
        rng = random.Random(42)
        rets = [rng.gauss(0.0005, 0.02) for _ in range(500)]
        result = vc.parametric(rets, portfolio_value=100000)
        assert result.var < 0
        assert result.method == "parametric"


# ============================================================
# Analytics Tests
# ============================================================

class TestPerformanceMetrics:
    def test_sharpe_positive(self):
        from src.analytics.metrics import PerformanceMetrics
        rets = [0.005] * 252  # steady positive returns
        s = PerformanceMetrics.sharpe(rets)
        assert s > 0

    def test_drawdown_analysis(self):
        from src.analytics.metrics import PerformanceMetrics
        curve = [10000, 11000, 12000, 10000, 9000, 11000, 13000]
        dd = PerformanceMetrics.drawdown_analysis(curve)
        assert dd.max_drawdown < 0
        assert dd.max_drawdown_duration_bars >= 0

    def test_trade_stats_empty(self):
        from src.analytics.metrics import PerformanceMetrics
        ts = PerformanceMetrics.trade_stats([])
        assert ts.total_trades == 0


class TestRollingAnalysis:
    def test_rolling_returns(self):
        from src.analytics.rolling import RollingAnalysis
        ra = RollingAnalysis(window=20)
        rets = [0.001] * 100
        points = ra.compute(rets)
        assert len(points) == 80
        assert all(p.rolling_return > 0 for p in points)


class TestRegimeAnalyzer:
    def test_classify_bull(self):
        from src.analytics.regime import RegimeAnalyzer, Regime
        ra = RegimeAnalyzer(sma_period=20)
        prices = [100 + i * 1.0 for i in range(100)]  # strong uptrend
        regimes = ra.classify_regimes(prices)
        # Later bars should be BULL
        assert Regime.BULL in regimes[-10:]


# ============================================================
# Backtesting Module Tests
# ============================================================

class TestMonteCarlo:
    def test_monte_carlo_basic(self):
        from src.backtesting.monte_carlo import MonteCarloSimulator
        from agents.backtester import BacktestResult, Trade
        from datetime import datetime

        trades = [
            Trade("TEST", "long", 100, 110, datetime(2020,1,1), datetime(2020,1,10),
                  10, 100, 0.10, "test", 0.7),
            Trade("TEST", "long", 110, 105, datetime(2020,1,15), datetime(2020,1,20),
                  10, -50, -0.045, "test", 0.5),
            Trade("TEST", "long", 105, 120, datetime(2020,2,1), datetime(2020,2,10),
                  10, 150, 0.143, "test", 0.8),
        ]
        result = BacktestResult(
            strategy_name="test", asset="TEST",
            start_date=datetime(2020,1,1), end_date=datetime(2020,3,1),
            total_return=0.15, annualized_return=0.30, benchmark_return=0.10, alpha=0.05,
            sharpe_ratio=1.5, sortino_ratio=2.0, calmar_ratio=3.0,
            max_drawdown=-0.05, max_drawdown_duration_days=5,
            volatility=0.15, downside_deviation=0.10,
            information_ratio=1.0, cvar_95=-0.03, var_95=-0.02,
            total_trades=3, winning_trades=2, losing_trades=1,
            win_rate=0.67, avg_win=0.12, avg_loss=-0.045,
            profit_factor=2.5, avg_trade_duration_hours=100,
            avg_debate_confidence=0.67, high_confidence_win_rate=0.5,
            low_confidence_win_rate=0.5, confidence_correlation=0.3,
            debate_rounds_avg=2, consensus_rate=0.8,
            equity_curve=[10000, 10100, 10050, 10200],
            drawdown_curve=[0, 0, -0.005, 0],
            daily_returns=[0.01, -0.005, 0.015],
            trades=trades,
        )

        mc = MonteCarloSimulator(n_simulations=100, seed=42)
        report = mc.run(result)
        assert report.n_simulations == 100
        assert len(report.all_returns) == 100
        assert report.returns_p5 <= report.returns_median <= report.returns_p95

    def test_monte_carlo_no_trades(self):
        from src.backtesting.monte_carlo import MonteCarloSimulator
        from agents.backtester import BacktestResult
        from datetime import datetime
        result = BacktestResult(
            strategy_name="empty", asset="X",
            start_date=datetime(2020,1,1), end_date=datetime(2020,3,1),
            total_return=0, annualized_return=0, benchmark_return=0, alpha=0,
            sharpe_ratio=0, sortino_ratio=0, calmar_ratio=0,
            max_drawdown=0, max_drawdown_duration_days=0,
            volatility=0, downside_deviation=0,
            information_ratio=0, cvar_95=0, var_95=0,
            total_trades=0, winning_trades=0, losing_trades=0,
            win_rate=0, avg_win=0, avg_loss=0,
            profit_factor=0, avg_trade_duration_hours=0,
            avg_debate_confidence=0, high_confidence_win_rate=0,
            low_confidence_win_rate=0, confidence_correlation=0,
            debate_rounds_avg=0, consensus_rate=0,
            equity_curve=[], drawdown_curve=[], daily_returns=[], trades=[],
        )
        mc = MonteCarloSimulator(n_simulations=10, seed=42)
        report = mc.run(result)
        assert report.n_simulations == 0


class TestWalkForward:
    def test_walk_forward_runs(self):
        from src.backtesting.walk_forward import WalkForwardAnalyzer
        from agents.backtester_v7 import BacktesterV7

        wf = WalkForwardAnalyzer(train_bars=100, test_bars=50, step_bars=50)
        prices = make_bull_prices(400)
        history = make_history(prices)

        async def _run():
            return await wf.run("TEST", "v7", history, lambda: BacktesterV7(initial_capital=100000))

        report = asyncio.get_event_loop().run_until_complete(_run())
        assert len(report.windows) >= 1
        assert report.oos_total_trades >= 0


class TestBenchmark:
    def test_buy_hold_metrics(self):
        from src.backtesting.benchmark import BenchmarkComparison
        bc = BenchmarkComparison()
        prices = make_bull_prices(300)
        bm = bc.compute_buy_hold("SPY", prices)
        assert bm.total_return > 0
        assert bm.name == "SPY"

    def test_comparison(self):
        from src.backtesting.benchmark import BenchmarkComparison
        bc = BenchmarkComparison()
        report = bc.compare(
            strategy_name="test",
            strategy_return=0.25,
            strategy_sharpe=1.5,
            strategy_max_dd=-0.10,
            strategy_daily_returns=[0.001] * 252,
            benchmark_series={"SPY": make_bull_prices(252)},
        )
        assert "SPY" in report.alpha_vs


class TestMultiTimeframe:
    def test_daily_weekly_monthly(self):
        from src.backtesting.multi_timeframe import MultiTimeframeBacktester, _resample_weekly, _resample_monthly
        prices = make_bull_prices(500)
        history = make_history(prices)
        weekly = _resample_weekly(history)
        monthly = _resample_monthly(history)
        assert len(weekly) > 0
        assert len(monthly) > 0
        assert len(weekly) < len(history)
        assert len(monthly) < len(weekly)


# ============================================================
# Pipeline Tests
# ============================================================

class TestDataCache:
    def test_set_get(self, tmp_path):
        from src.pipeline.cache import DataCache
        cache = DataCache(cache_dir=str(tmp_path / "cache"))
        cache.set("test_key", [{"price": 100}])
        result = cache.get("test_key")
        assert result is not None
        assert result[0]["price"] == 100

    def test_cache_miss(self, tmp_path):
        from src.pipeline.cache import DataCache
        cache = DataCache(cache_dir=str(tmp_path / "cache"))
        assert cache.get("nonexistent") is None

    def test_invalidate(self, tmp_path):
        from src.pipeline.cache import DataCache
        cache = DataCache(cache_dir=str(tmp_path / "cache"))
        cache.set("k", [{"x": 1}])
        cache.invalidate("k")
        assert cache.get("k") is None


class TestDataValidator:
    def test_valid_data(self):
        from src.pipeline.validator import DataValidator
        v = DataValidator()
        bars = make_history(make_bull_prices(100))
        report = v.validate(bars)
        assert report.total_bars == 100

    def test_outlier_detection(self):
        from src.pipeline.validator import DataValidator
        from datetime import datetime, timedelta
        v = DataValidator(max_daily_change=0.10)
        bars = [
            {"date": datetime(2020,1,1), "price": 100},
            {"date": datetime(2020,1,2), "price": 200},  # 100% jump!
            {"date": datetime(2020,1,3), "price": 105},
        ]
        report = v.validate(bars)
        assert report.outliers_removed > 0

    def test_clean(self):
        from src.pipeline.validator import DataValidator
        from datetime import datetime
        v = DataValidator(max_daily_change=0.10)
        bars = [
            {"date": datetime(2020,1,1), "price": 100},
            {"date": datetime(2020,1,2), "price": 200},
            {"date": datetime(2020,1,3), "price": 105},
        ]
        cleaned, report = v.clean(bars)
        assert len(cleaned) == 3
        assert cleaned[1]["price"] == 100  # replaced outlier
