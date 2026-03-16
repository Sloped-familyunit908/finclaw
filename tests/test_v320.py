"""Tests for v3.2.0 — Risk Analytics Deep Dive.

Covers: AdvancedRiskMetrics, StressTester, RiskBudgeter, LiquidityAnalyzer.
30+ tests total.
"""

import math
import pytest
from src.risk.advanced_metrics import AdvancedRiskMetrics
from src.risk.stress_test import StressTester, Portfolio
from src.risk.risk_budget import RiskBudgeter
from src.analytics.liquidity import LiquidityAnalyzer, LiquidityData


# ── AdvancedRiskMetrics ──────────────────────────────────────────────

class TestConditionalVaR:
    def test_basic(self):
        returns = [-0.05, -0.03, -0.01, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07,
                   -0.04, -0.02, 0.0, 0.01, 0.03, 0.05, 0.06, 0.08, 0.09, 0.10]
        cvar = AdvancedRiskMetrics.conditional_var(returns, 0.95)
        assert cvar > 0

    def test_empty(self):
        assert AdvancedRiskMetrics.conditional_var([]) == 0.0

    def test_all_positive(self):
        returns = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10]
        cvar = AdvancedRiskMetrics.conditional_var(returns, 0.95)
        # CVaR is -mean of tail, which for positive returns is negative → returned as positive of that
        assert isinstance(cvar, float)

    def test_all_negative(self):
        returns = [-0.10, -0.09, -0.08, -0.07, -0.06, -0.05, -0.04, -0.03, -0.02, -0.01]
        cvar = AdvancedRiskMetrics.conditional_var(returns, 0.95)
        assert cvar > 0.05  # Worst tail is ~-0.10


class TestOmegaRatio:
    def test_positive_returns(self):
        returns = [0.01, 0.02, 0.03, 0.04, 0.05]
        omega = AdvancedRiskMetrics.omega_ratio(returns)
        assert omega == float('inf')  # No losses

    def test_mixed(self):
        returns = [-0.02, -0.01, 0.01, 0.02, 0.03]
        omega = AdvancedRiskMetrics.omega_ratio(returns)
        assert omega > 1.0  # More gains than losses

    def test_empty(self):
        assert AdvancedRiskMetrics.omega_ratio([]) == 0.0

    def test_threshold(self):
        returns = [0.01, 0.02, 0.03, -0.01, -0.02]
        omega_0 = AdvancedRiskMetrics.omega_ratio(returns, 0.0)
        omega_high = AdvancedRiskMetrics.omega_ratio(returns, 0.02)
        assert omega_0 > omega_high  # Higher threshold → lower omega


class TestTailRatio:
    def test_needs_data(self):
        assert AdvancedRiskMetrics.tail_ratio([0.01] * 10) == 0.0  # Too few

    def test_symmetric(self):
        import random
        random.seed(42)
        returns = [random.gauss(0, 0.02) for _ in range(100)]
        ratio = AdvancedRiskMetrics.tail_ratio(returns)
        assert 0.5 < ratio < 2.0  # Roughly symmetric


class TestDownsideDeviation:
    def test_no_downside(self):
        returns = [0.01, 0.02, 0.03]
        assert AdvancedRiskMetrics.downside_deviation(returns) == 0.0

    def test_all_downside(self):
        returns = [-0.01, -0.02, -0.03]
        dd = AdvancedRiskMetrics.downside_deviation(returns)
        assert dd > 0

    def test_empty(self):
        assert AdvancedRiskMetrics.downside_deviation([]) == 0.0


class TestInformationRatio:
    def test_basic(self):
        ret = [0.02, 0.03, 0.01, 0.04, 0.02]
        bench = [0.01, 0.01, 0.01, 0.01, 0.01]
        ir = AdvancedRiskMetrics.information_ratio(ret, bench)
        assert ir > 0  # Outperforming

    def test_matching(self):
        ret = [0.01, 0.02, 0.03]
        ir = AdvancedRiskMetrics.information_ratio(ret, ret)
        assert ir == 0.0  # Zero tracking error

    def test_empty(self):
        assert AdvancedRiskMetrics.information_ratio([], []) == 0.0


class TestTreynorRatio:
    def test_basic(self):
        ret = [0.02, 0.03, 0.01, 0.04, 0.02]
        bench = [0.01, 0.02, 0.005, 0.03, 0.015]
        tr = AdvancedRiskMetrics.treynor_ratio(ret, bench)
        assert isinstance(tr, float)

    def test_zero_benchmark_var(self):
        ret = [0.01, 0.02, 0.03]
        bench = [0.01, 0.01, 0.01]
        assert AdvancedRiskMetrics.treynor_ratio(ret, bench) == 0.0


class TestCaptureRatio:
    def test_basic(self):
        ret = [0.02, -0.01, 0.03, -0.02, 0.01]
        bench = [0.01, -0.02, 0.02, -0.01, 0.015]
        result = AdvancedRiskMetrics.capture_ratio(ret, bench)
        assert 'up_capture' in result
        assert 'down_capture' in result
        assert 'capture_ratio' in result

    def test_empty(self):
        result = AdvancedRiskMetrics.capture_ratio([], [])
        assert result['up_capture'] == 0.0


# ── StressTester ─────────────────────────────────────────────────────

class TestStressTester:
    def setup_method(self):
        self.tester = StressTester()
        self.portfolio = Portfolio(
            holdings={'SPY': 0.6, 'QQQ': 0.3, 'BND': 0.1},
            total_value=100_000,
            beta=1.1,
            bond_weight=0.1,
        )

    def test_run_2008(self):
        result = self.tester.run_scenario(self.portfolio, '2008_financial_crisis')
        assert result['loss_pct'] > 0.3
        assert result['stressed_value'] < 100_000

    def test_run_covid(self):
        result = self.tester.run_scenario(self.portfolio, 'covid_crash')
        assert result['loss_pct'] > 0.2

    def test_run_rate_hike(self):
        result = self.tester.run_scenario(self.portfolio, 'rate_hike_2022')
        assert result['loss_pct'] > 0.1

    def test_unknown_scenario(self):
        with pytest.raises(ValueError, match="Unknown scenario"):
            self.tester.run_scenario(self.portfolio, 'alien_invasion')

    def test_custom_scenario(self):
        result = self.tester.custom_scenario(self.portfolio, {'market': -0.25})
        assert result['loss_pct'] > 0.2
        assert result['scenario'] == 'custom'

    def test_reverse_stress(self):
        result = self.tester.reverse_stress(self.portfolio, 0.30)
        assert 'triggering_scenarios' in result
        assert result['required_market_drop'] < 0

    def test_reverse_stress_invalid(self):
        with pytest.raises(ValueError):
            self.tester.reverse_stress(self.portfolio, 0.0)

    def test_all_scenarios_run(self):
        for scenario in StressTester.SCENARIOS:
            result = self.tester.run_scenario(self.portfolio, scenario)
            assert 'loss_pct' in result


# ── RiskBudgeter ─────────────────────────────────────────────────────

class TestRiskBudgeter:
    def setup_method(self):
        self.budgeter = RiskBudgeter()
        self.portfolio = {
            'stocks': {'vol': 0.20, 'weight': 0.60},
            'bonds': {'vol': 0.05, 'weight': 0.30},
            'gold': {'vol': 0.15, 'weight': 0.10},
        }

    def test_allocate(self):
        budget = self.budgeter.allocate(0.15, self.portfolio)
        assert len(budget) == 3
        assert all(v > 0 for v in budget.values())

    def test_allocate_empty(self):
        assert self.budgeter.allocate(0.15, {}) == {}

    def test_marginal_risk(self):
        mr = self.budgeter.marginal_risk(self.portfolio, 'stocks')
        assert mr > 0

    def test_marginal_risk_missing(self):
        assert self.budgeter.marginal_risk(self.portfolio, 'crypto') == 0.0

    def test_risk_contribution(self):
        rc = self.budgeter.risk_contribution(self.portfolio)
        assert 'stocks' in rc
        assert rc['stocks']['pct_of_total'] > rc['bonds']['pct_of_total']

    def test_rebalance(self):
        target = {'stocks': 50.0, 'bonds': 30.0, 'gold': 20.0}
        trades = self.budgeter.rebalance_to_risk_target(self.portfolio, target)
        assert isinstance(trades, list)

    def test_rebalance_empty(self):
        assert self.budgeter.rebalance_to_risk_target({}, {}) == []


# ── LiquidityAnalyzer ────────────────────────────────────────────────

class TestLiquidityAnalyzer:
    def setup_method(self):
        self.analyzer = LiquidityAnalyzer()
        self.data = [
            LiquidityData(close=100 + i * 0.5, volume=1_000_000 + i * 10000,
                          high=101 + i * 0.5, low=99 + i * 0.5)
            for i in range(30)
        ]

    def test_analyze_basic(self):
        result = self.analyzer.analyze('AAPL', self.data)
        assert result['ticker'] == 'AAPL'
        assert result['avg_volume'] > 0
        assert result['avg_dollar_volume'] > 0
        assert result['bid_ask_spread_est'] > 0

    def test_analyze_empty(self):
        result = self.analyzer.analyze('EMPTY', [])
        assert result['avg_volume'] == 0

    def test_amihud(self):
        result = self.analyzer.analyze('TEST', self.data)
        assert result['amihud_illiquidity'] >= 0

    def test_portfolio_liquidity(self):
        liq_aapl = self.analyzer.analyze('AAPL', self.data)
        holdings = {
            'AAPL': {'weight': 0.5, 'liquidity': liq_aapl},
            'MSFT': {'weight': 0.5, 'liquidity': liq_aapl},
        }
        result = self.analyzer.portfolio_liquidity(holdings)
        assert result['holdings'] == 2
        assert result['weighted_spread'] > 0

    def test_portfolio_empty(self):
        result = self.analyzer.portfolio_liquidity({})
        assert result['holdings'] == 0


# ── Import Tests ─────────────────────────────────────────────────────

class TestImports:
    def test_risk_imports(self):
        from src.risk import AdvancedRiskMetrics, StressTester, Portfolio, RiskBudgeter
        assert AdvancedRiskMetrics is not None
        assert StressTester is not None

    def test_analytics_imports(self):
        from src.analytics import LiquidityAnalyzer, LiquidityData
        assert LiquidityAnalyzer is not None
