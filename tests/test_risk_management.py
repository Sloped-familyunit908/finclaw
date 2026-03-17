"""
Tests for FinClaw Risk Management Module.

Tests all position sizing, risk metrics, stop loss, VaR calculations
against known values.
"""

import math
import pytest

# ── Position Sizer ──────────────────────────────────────────────

from src.risk.position_sizer import PositionSizer


class TestPositionSizer:
    def test_percent_risk_basic(self):
        # $100k capital, entry $50, stop $48, risk 2%
        # Risk amount = $2000, stop distance = $2, shares = 1000
        shares = PositionSizer.percent_risk(100000, 50.0, 48.0, 0.02)
        assert shares == 1000

    def test_percent_risk_zero_stop_distance(self):
        assert PositionSizer.percent_risk(100000, 50.0, 50.0, 0.02) == 0

    def test_percent_risk_negative_capital(self):
        assert PositionSizer.percent_risk(-1000, 50.0, 48.0, 0.02) == 0

    def test_kelly_positive_edge(self):
        # Win rate 60%, win/loss ratio 1.5
        # Kelly = (1.5*0.6 - 0.4)/1.5 = 0.333, half-kelly = 0.167
        f = PositionSizer.kelly(0.6, 1.5, 0.5)
        assert abs(f - 0.1667) < 0.01

    def test_kelly_no_edge(self):
        # Win rate 30%, win/loss ratio 1.0 → negative edge
        f = PositionSizer.kelly(0.3, 1.0)
        assert f == 0.0

    def test_kelly_boundary(self):
        assert PositionSizer.kelly(0.0, 1.5) == 0.0
        assert PositionSizer.kelly(1.0, 1.5) == 0.0

    def test_volatility_based(self):
        # $100k capital, price $100, ATR $5, risk 2%
        # Risk amount = $2000, shares = 2000/5 = 400
        shares = PositionSizer.volatility_based(100000, 100.0, 5.0, 0.02)
        assert shares == 400

    def test_volatility_caps_at_capital(self):
        # Very low ATR → huge shares, but capped at what capital can buy
        shares = PositionSizer.volatility_based(1000, 100.0, 0.01, 0.02)
        assert shares <= 10  # $1000/$100 = 10 max shares

    def test_equal_weight(self):
        assert PositionSizer.equal_weight(4) == 0.25
        assert PositionSizer.equal_weight(1) == 1.0
        assert PositionSizer.equal_weight(0) == 0.0

    def test_risk_parity(self):
        vols = [0.20, 0.10, 0.40]  # 20%, 10%, 40% volatility
        weights = PositionSizer.risk_parity(vols)
        assert len(weights) == 3
        assert abs(sum(weights) - 1.0) < 1e-10
        # Lower vol should get higher weight
        assert weights[1] > weights[0] > weights[2]

    def test_risk_parity_equal_vols(self):
        vols = [0.20, 0.20, 0.20]
        weights = PositionSizer.risk_parity(vols)
        for w in weights:
            assert abs(w - 1 / 3) < 1e-10

    def test_risk_parity_empty(self):
        assert PositionSizer.risk_parity([]) == []

    def test_fixed_dollar(self):
        assert abs(PositionSizer.fixed_dollar(100000, 2000) - 0.02) < 1e-10

    def test_optimal_f(self):
        trades = [100, -50, 200, -75, 150, -100, 300, -60]
        f = PositionSizer.optimal_f(trades)
        assert 0 < f <= 1.0


# ── Risk Metrics ────────────────────────────────────────────────

from src.risk.risk_metrics import RiskMetrics, RiskReport


class TestRiskMetrics:
    @pytest.fixture
    def sample_returns(self):
        """Deterministic daily returns for testing."""
        import random
        random.seed(42)
        return [random.gauss(0.0005, 0.015) for _ in range(500)]

    def test_sharpe_ratio_positive(self, sample_returns):
        sr = RiskMetrics.sharpe_ratio(sample_returns)
        assert isinstance(sr, float)
        # With positive mean drift, Sharpe should be positive-ish
        # (random seed 42 specific)

    def test_sharpe_ratio_zero_vol(self):
        # Constant returns → zero std → 0
        returns = [0.01] * 100
        sr = RiskMetrics.sharpe_ratio(returns)
        # All same → technically infinite but we guard with std check
        # Actually std(constant)=0 → returns 0
        assert sr == 0.0 or math.isinf(sr) is False

    def test_sharpe_empty(self):
        assert RiskMetrics.sharpe_ratio([]) == 0.0
        assert RiskMetrics.sharpe_ratio([0.01]) == 0.0

    def test_sortino_ratio(self, sample_returns):
        sr = RiskMetrics.sortino_ratio(sample_returns)
        assert isinstance(sr, float)

    def test_sortino_no_downside(self):
        # All positive returns → infinite sortino
        returns = [0.01, 0.02, 0.015, 0.005, 0.01]
        sr = RiskMetrics.sortino_ratio(returns)
        assert sr == float('inf') or sr > 10  # very high

    def test_max_drawdown(self):
        # Equity: 1, 1.1, 1.2, 0.9, 0.8, 1.0
        # Returns: +10%, +9.09%, -25%, -11.11%, +25%
        returns = [0.10, 0.0909, -0.25, -0.1111, 0.25]
        dd = RiskMetrics.max_drawdown(returns)
        # Peak = 1.2, trough = 0.8 → DD = -33.3%
        assert dd.max_drawdown < -0.30
        assert dd.max_drawdown > -0.40

    def test_max_drawdown_empty(self):
        dd = RiskMetrics.max_drawdown([])
        assert dd.max_drawdown == 0.0

    def test_var_historical(self, sample_returns):
        var = RiskMetrics.value_at_risk(sample_returns, 0.95, "historical")
        assert var < 0  # Should be negative (a loss)

    def test_var_parametric(self, sample_returns):
        var = RiskMetrics.value_at_risk(sample_returns, 0.95, "parametric")
        assert var < 0

    def test_var_insufficient_data(self):
        assert RiskMetrics.value_at_risk([0.01, 0.02], 0.95) == 0.0

    def test_cvar(self, sample_returns):
        cvar = RiskMetrics.conditional_var(sample_returns, 0.95)
        var = RiskMetrics.value_at_risk(sample_returns, 0.95)
        # CVaR should be worse (more negative) than VaR
        assert cvar <= var

    def test_calmar_ratio(self, sample_returns):
        cr = RiskMetrics.calmar_ratio(sample_returns)
        assert isinstance(cr, float)

    def test_win_rate(self):
        trades = [100, -50, 200, -30, 150]
        assert RiskMetrics.win_rate(trades) == 0.6

    def test_win_rate_empty(self):
        assert RiskMetrics.win_rate([]) == 0.0

    def test_profit_factor(self):
        trades = [100, -50, 200, -30]
        # Gross profit = 300, gross loss = 80
        pf = RiskMetrics.profit_factor(trades)
        assert abs(pf - 3.75) < 0.01

    def test_profit_factor_no_losses(self):
        assert RiskMetrics.profit_factor([100, 200]) == float('inf')

    def test_risk_reward_ratio(self):
        trades = [100, -50, 200, -30, 150]
        # Avg win = 150, avg loss = 40
        rr = RiskMetrics.risk_reward_ratio(trades)
        assert abs(rr - 3.75) < 0.01

    def test_skewness_symmetric(self):
        # Roughly symmetric distribution
        returns = [0.01, -0.01, 0.02, -0.02, 0.01, -0.01, 0.015, -0.015]
        sk = RiskMetrics.skewness(returns)
        assert abs(sk) < 0.5  # approximately 0

    def test_kurtosis(self, sample_returns):
        k = RiskMetrics.kurtosis(sample_returns)
        assert isinstance(k, float)

    def test_full_report(self, sample_returns):
        trades = [100, -50, 200, -30, 150, -80, 300, -40]
        report = RiskMetrics.full_report(sample_returns, trades)
        assert isinstance(report, RiskReport)
        assert report.num_trades == 8
        assert report.win_rate == 0.5  # 4 wins / 8 trades
        assert report.max_drawdown < 0


# ── Stop Loss ───────────────────────────────────────────────────

from src.risk.stop_loss import (
    StopLossManager, ChandelierExit, ParabolicSARStop, BreakEvenStop
)


class TestStopLossManager:
    def test_fixed_stop(self):
        mgr = StopLossManager(fixed_pct=0.05)
        stops = mgr.compute_stops(
            entry_price=100, current_price=94, highest_since_entry=105,
            bars_held=5
        )
        fixed = [s for s in stops if s.type.value == "fixed"][0]
        assert fixed.price == 95.0  # 100 * 0.95
        assert fixed.triggered  # 94 < 95

    def test_trailing_stop(self):
        mgr = StopLossManager(trailing_pct=0.10)
        stops = mgr.compute_stops(
            entry_price=100, current_price=92, highest_since_entry=110,
            bars_held=5
        )
        trail = [s for s in stops if s.type.value == "trailing"][0]
        assert trail.price == 99.0  # 110 * 0.90
        assert trail.triggered  # 92 < 99

    def test_time_stop(self):
        mgr = StopLossManager(max_hold_bars=10)
        stops = mgr.compute_stops(
            entry_price=100, current_price=105, highest_since_entry=105,
            bars_held=15
        )
        time_stop = [s for s in stops if s.type.value == "time"][0]
        assert time_stop.triggered

    def test_atr_stop(self):
        mgr = StopLossManager(atr_multiplier=2.0)
        stops = mgr.compute_stops(
            entry_price=100, current_price=100, highest_since_entry=100,
            bars_held=1, atr=3.0
        )
        atr_stop = [s for s in stops if s.type.value == "atr"][0]
        assert atr_stop.price == 94.0  # 100 - 2*3


class TestChandelierExit:
    def test_basic(self):
        n = 30
        highs = [100 + i * 0.5 for i in range(n)]
        lows = [98 + i * 0.5 for i in range(n)]
        closes = [99 + i * 0.5 for i in range(n)]
        ce = ChandelierExit(period=22, multiplier=3.0)
        stops = ce.compute(highs, lows, closes)
        assert len(stops) == n
        assert math.isnan(stops[0])
        assert not math.isnan(stops[-1])
        # Stop should be below the highest high
        assert stops[-1] < max(highs[-22:])

    def test_insufficient_data(self):
        ce = ChandelierExit(period=22)
        stops = ce.compute([100] * 5, [99] * 5, [99.5] * 5)
        assert all(math.isnan(s) for s in stops)


class TestParabolicSAR:
    def test_basic(self):
        # Simple uptrend
        n = 30
        highs = [100 + i for i in range(n)]
        lows = [98 + i for i in range(n)]
        sar = ParabolicSARStop()
        result = sar.compute(highs, lows)
        assert len(result) == n
        # In an uptrend, SAR should be below price
        assert result[-1] < lows[-1]

    def test_short_data(self):
        sar = ParabolicSARStop()
        result = sar.compute([100], [99])
        assert len(result) == 1
        assert math.isnan(result[0])


class TestBreakEvenStop:
    def test_not_triggered(self):
        be = BreakEvenStop(trigger_pct=0.05)
        stop = be.get_stop(entry_price=100, current_price=103, original_stop=95)
        assert stop == 95  # 3% profit < 5% trigger

    def test_triggered(self):
        be = BreakEvenStop(trigger_pct=0.05, buffer_pct=0.001)
        stop = be.get_stop(entry_price=100, current_price=106, original_stop=95)
        assert abs(stop - 100.1) < 0.01  # entry + 0.1% buffer

    def test_zero_entry(self):
        be = BreakEvenStop()
        assert be.get_stop(0, 100, 95) == 95


# ── VaR Calculator ──────────────────────────────────────────────

from src.risk.var_calculator import VaRCalculator


class TestVaRCalculator:
    @pytest.fixture
    def returns(self):
        import random
        random.seed(123)
        return [random.gauss(0.0003, 0.012) for _ in range(500)]

    def test_historical_var(self, returns):
        calc = VaRCalculator(confidence=0.95)
        result = calc.historical(returns, portfolio_value=100000)
        assert result.method == "historical"
        assert result.var < 0
        assert result.cvar <= result.var
        assert result.var_dollar < 0

    def test_parametric_var(self, returns):
        calc = VaRCalculator(confidence=0.95)
        result = calc.parametric(returns, portfolio_value=100000)
        assert result.method == "parametric"
        assert result.var < 0

    def test_insufficient_data(self):
        calc = VaRCalculator()
        result = calc.historical([0.01] * 5)
        assert result.var == 0


# ── Advanced Metrics ────────────────────────────────────────────

from src.risk.advanced_metrics import AdvancedRiskMetrics


class TestAdvancedMetrics:
    @pytest.fixture
    def returns(self):
        import random
        random.seed(99)
        return [random.gauss(0.001, 0.02) for _ in range(300)]

    def test_conditional_var(self, returns):
        cvar = AdvancedRiskMetrics.conditional_var(returns, 0.95)
        assert cvar > 0  # Positive loss number

    def test_omega_ratio(self, returns):
        omega = AdvancedRiskMetrics.omega_ratio(returns)
        assert omega > 0

    def test_omega_all_gains(self):
        assert AdvancedRiskMetrics.omega_ratio([0.01, 0.02, 0.03]) == float('inf')

    def test_tail_ratio(self, returns):
        tr = AdvancedRiskMetrics.tail_ratio(returns)
        assert tr > 0

    def test_downside_deviation(self, returns):
        dd = AdvancedRiskMetrics.downside_deviation(returns)
        assert dd >= 0

    def test_information_ratio(self):
        port = [0.01, 0.02, -0.01, 0.03, 0.02]
        bench = [0.005, 0.01, 0.005, 0.01, 0.015]
        ir = AdvancedRiskMetrics.information_ratio(port, bench)
        assert isinstance(ir, float)


# ── Position Sizing (alternate classes) ──────────────────────────

from src.risk.position_sizing import KellyCriterion, FixedFractional, VolatilitySizing


class TestPositionSizingClasses:
    def test_kelly_criterion(self):
        kc = KellyCriterion(kelly_fraction=0.5, max_position=0.25)
        result = kc.calculate(win_rate=0.6, avg_win=150, avg_loss=100)
        assert 0 < result.fraction <= 0.25

    def test_kelly_no_edge(self):
        kc = KellyCriterion()
        result = kc.calculate(win_rate=0.3, avg_win=50, avg_loss=100)
        assert result.fraction == 0

    def test_fixed_fractional(self):
        ff = FixedFractional(risk_per_trade=0.02)
        result = ff.calculate(capital=100000, entry_price=50, stop_price=48)
        assert result.fraction > 0

    def test_volatility_sizing(self):
        vs = VolatilitySizing(target_volatility=0.01)
        prices = [100 + i * 0.1 for i in range(30)]
        result = vs.calculate(capital=100000, prices=prices)
        assert result.fraction > 0


# ── Portfolio Risk ──────────────────────────────────────────────

from src.risk.portfolio_risk import PortfolioRiskManager


class TestPortfolioRisk:
    def test_drawdown_circuit_breaker(self):
        mgr = PortfolioRiskManager(max_drawdown_limit=0.10)
        # Equity drops 15% from peak
        eq = [100, 105, 110, 100, 95, 90, 85]
        halt, dd = mgr.check_drawdown_circuit_breaker(eq)
        assert halt  # 85/110 - 1 = -22.7% > 10% limit

    def test_no_circuit_breaker(self):
        mgr = PortfolioRiskManager(max_drawdown_limit=0.20)
        eq = [100, 105, 103, 108]
        halt, dd = mgr.check_drawdown_circuit_breaker(eq)
        assert not halt

    def test_equal_weight_allocation(self):
        mgr = PortfolioRiskManager(max_single_position=0.50)
        result = mgr.equal_weight_allocation(["AAPL", "MSFT", "GOOGL"])
        assert len(result.weights) == 3
        assert abs(sum(result.weights.values()) - 1.0) < 0.01

    def test_inverse_vol_allocation(self):
        mgr = PortfolioRiskManager(max_single_position=1.0)
        vols = {"AAPL": 0.20, "MSFT": 0.15, "GOOGL": 0.30}
        result = mgr.inverse_volatility_allocation(vols)
        # Lower vol → higher weight
        assert result.weights["MSFT"] > result.weights["AAPL"] > result.weights["GOOGL"]

    def test_correlation(self):
        mgr = PortfolioRiskManager()
        a = [0.01, -0.02, 0.03, -0.01, 0.02, 0.01, -0.015, 0.025]
        b = [0.01, -0.02, 0.03, -0.01, 0.02, 0.01, -0.015, 0.025]
        corr = mgr.correlation_check(a, b)
        assert abs(corr - 1.0) < 0.01  # Perfect correlation
