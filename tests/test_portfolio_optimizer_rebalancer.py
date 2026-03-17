"""Tests for v4.5.0 — Portfolio Optimizer, Rebalancer, TaxLotTracker, PerformanceAttribution."""

import math
import random
from datetime import date, timedelta

import pytest

from src.portfolio.optimizer import PortfolioOptimizer, _mean, _cov_matrix
from src.portfolio.rebalancer import Rebalancer
from src.portfolio.tax_tracker import TaxLotTracker, TaxResult, HarvestCandidate
from src.portfolio.attribution import PerformanceAttribution, SectorAllocation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_returns(n_assets=3, n_days=252, seed=42):
    """Generate reproducible fake daily returns."""
    rng = random.Random(seed)
    tickers = [f"ASSET{i}" for i in range(n_assets)]
    returns = {}
    for t in tickers:
        base = rng.uniform(-0.0005, 0.001)
        returns[t] = [base + rng.gauss(0, 0.015) for _ in range(n_days)]
    return returns


# ===========================================================================
#  1. Portfolio Optimizer
# ===========================================================================

class TestPortfolioOptimizer:
    """Tests for PortfolioOptimizer (12 tests)."""

    def test_min_variance_weights_sum_to_one(self):
        ret = _fake_returns()
        result = PortfolioOptimizer.min_variance(ret)
        assert abs(sum(result["weights"].values()) - 1.0) < 0.01

    def test_min_variance_positive_weights(self):
        ret = _fake_returns()
        result = PortfolioOptimizer.min_variance(ret)
        for w in result["weights"].values():
            assert w >= -0.01  # long-only

    def test_max_sharpe_returns_sharpe(self):
        ret = _fake_returns()
        result = PortfolioOptimizer.max_sharpe(ret, risk_free=0.02)
        assert "sharpe_ratio" in result
        assert isinstance(result["sharpe_ratio"], float)

    def test_max_sharpe_weights_sum_to_one(self):
        ret = _fake_returns()
        result = PortfolioOptimizer.max_sharpe(ret)
        assert abs(sum(result["weights"].values()) - 1.0) < 0.01

    def test_mean_variance_with_target(self):
        ret = _fake_returns()
        result = PortfolioOptimizer.mean_variance(ret, target_return=0.05)
        assert "weights" in result
        assert abs(sum(result["weights"].values()) - 1.0) < 0.01

    def test_mean_variance_no_target_delegates_to_max_sharpe(self):
        ret = _fake_returns()
        r1 = PortfolioOptimizer.mean_variance(ret)
        r2 = PortfolioOptimizer.max_sharpe(ret)
        # Should be same since mean_variance without target → max_sharpe
        assert r1["weights"] == r2["weights"]

    def test_risk_parity_equal_risk(self):
        ret = _fake_returns(n_assets=3)
        result = PortfolioOptimizer.risk_parity(ret)
        assert abs(sum(result["weights"].values()) - 1.0) < 0.01
        rc = list(result["risk_contributions"].values())
        # Risk contributions should be roughly equal
        avg_rc = sum(rc) / len(rc)
        for r in rc:
            assert abs(r - avg_rc) < avg_rc * 2  # within 2x of mean

    def test_black_litterman_no_views(self):
        ret = _fake_returns()
        caps = {t: 1000.0 for t in ret}
        result = PortfolioOptimizer.black_litterman(ret, caps, [], [])
        assert abs(sum(result["weights"].values()) - 1.0) < 0.01

    def test_black_litterman_with_views(self):
        ret = _fake_returns()
        tickers = sorted(ret.keys())
        caps = {t: 1000.0 for t in tickers}
        views = [{"assets": {tickers[0]: 1.0}, "return": 0.10}]
        confidence = [0.8]
        result = PortfolioOptimizer.black_litterman(ret, caps, views, confidence)
        assert "weights" in result
        assert "bl_returns" in result

    def test_efficient_frontier_returns_points(self):
        ret = _fake_returns()
        frontier = PortfolioOptimizer.efficient_frontier(ret, n_points=10)
        assert len(frontier) == 10
        for pt in frontier:
            assert "weights" in pt
            assert "volatility" in pt

    def test_efficient_frontier_volatility_ordering(self):
        ret = _fake_returns()
        frontier = PortfolioOptimizer.efficient_frontier(ret, n_points=20)
        # Returns should be monotonically increasing
        rets = [p["expected_return"] for p in frontier]
        for i in range(1, len(rets)):
            assert rets[i] >= rets[i - 1] - 0.01

    def test_empty_returns(self):
        result = PortfolioOptimizer.min_variance({})
        assert result["weights"] == {}


# ===========================================================================
#  2. Rebalancer (simplified API)
# ===========================================================================

class TestRebalancer:
    """Tests for the Rebalancer spec API (10 tests)."""

    def test_check_drift_no_drift(self):
        r = Rebalancer({"SPY": 0.6, "TLT": 0.4})
        result = r.check_drift({"SPY": 0.6, "TLT": 0.4})
        assert result["max_drift"] < 0.001
        assert result["needs_rebalance"] is False

    def test_check_drift_with_drift(self):
        r = Rebalancer({"SPY": 0.6, "TLT": 0.4}, threshold=0.05)
        result = r.check_drift({"SPY": 0.7, "TLT": 0.3})
        assert result["max_drift"] == pytest.approx(0.1, abs=0.001)
        assert result["needs_rebalance"] is True

    def test_check_drift_below_threshold(self):
        r = Rebalancer({"SPY": 0.6, "TLT": 0.4}, threshold=0.05)
        result = r.check_drift({"SPY": 0.62, "TLT": 0.38})
        assert result["needs_rebalance"] is False

    def test_generate_trades_basic(self):
        r = Rebalancer({"SPY": 0.6, "TLT": 0.4})
        current = {"SPY": 7000, "TLT": 3000}  # 70/30 split
        prices = {"SPY": 500, "TLT": 100}
        trades = r.generate_trades(current, prices)
        assert len(trades) == 2
        actions = {t["symbol"]: t["action"] for t in trades}
        assert actions["SPY"] == "sell"
        assert actions["TLT"] == "buy"

    def test_generate_trades_no_trades_needed(self):
        r = Rebalancer({"SPY": 0.6, "TLT": 0.4})
        current = {"SPY": 6000, "TLT": 4000}
        prices = {"SPY": 500, "TLT": 100}
        trades = r.generate_trades(current, prices)
        assert len(trades) == 0  # Already balanced

    def test_generate_trades_empty(self):
        r = Rebalancer({"SPY": 1.0})
        trades = r.generate_trades({}, {})
        assert trades == []

    def test_calendar_rebalance(self):
        r = Rebalancer({"SPY": 1.0})
        assert r.calendar_rebalance("monthly") is True

    def test_band_rebalance_true(self):
        r = Rebalancer({"SPY": 0.5, "TLT": 0.5}, threshold=0.05)
        assert r.band_rebalance({"SPY": 7000, "TLT": 3000}) is True

    def test_band_rebalance_false(self):
        r = Rebalancer({"SPY": 0.5, "TLT": 0.5}, threshold=0.05)
        assert r.band_rebalance({"SPY": 5100, "TLT": 4900}) is False

    def test_band_rebalance_empty(self):
        r = Rebalancer({"SPY": 1.0})
        assert r.band_rebalance({}) is False


# ===========================================================================
#  3. Tax Lot Tracker
# ===========================================================================

class TestTaxLotTracker:
    """Tests for TaxLotTracker (12 tests)."""

    def test_add_lot(self):
        t = TaxLotTracker()
        lot = t.add_lot("AAPL", 100, 150.0, date(2024, 1, 15))
        assert lot.shares == 100
        assert lot.price == 150.0

    def test_add_multiple_lots(self):
        t = TaxLotTracker()
        t.add_lot("AAPL", 100, 150.0, date(2024, 1, 15))
        t.add_lot("AAPL", 50, 160.0, date(2024, 6, 1))
        lots = t.get_lots("AAPL")
        assert len(lots) == 2
        assert sum(l.shares for l in lots) == 150

    def test_sell_fifo(self):
        t = TaxLotTracker()
        t.add_lot("AAPL", 100, 150.0, date(2024, 1, 15))
        t.add_lot("AAPL", 100, 170.0, date(2024, 6, 1))
        result = t.sell("AAPL", 100, 180.0, date(2025, 3, 1), method="FIFO")
        assert result.cost_basis == pytest.approx(15000.0)
        assert result.realized_gain == pytest.approx(3000.0)
        assert result.is_long_term is True

    def test_sell_lifo(self):
        t = TaxLotTracker()
        t.add_lot("AAPL", 100, 150.0, date(2024, 1, 15))
        t.add_lot("AAPL", 100, 170.0, date(2024, 6, 1))
        result = t.sell("AAPL", 100, 180.0, date(2025, 3, 1), method="LIFO")
        assert result.cost_basis == pytest.approx(17000.0)
        assert result.realized_gain == pytest.approx(1000.0)

    def test_sell_highest_cost(self):
        t = TaxLotTracker()
        t.add_lot("AAPL", 100, 150.0, date(2024, 1, 15))
        t.add_lot("AAPL", 100, 180.0, date(2024, 3, 1))
        t.add_lot("AAPL", 100, 160.0, date(2024, 6, 1))
        result = t.sell("AAPL", 100, 170.0, date(2025, 3, 1), method="HighestCost")
        assert result.cost_basis == pytest.approx(18000.0)
        assert result.realized_gain == pytest.approx(-1000.0)

    def test_sell_tax_optimal(self):
        t = TaxLotTracker()
        t.add_lot("AAPL", 50, 200.0, date(2024, 1, 1))  # loss at 180
        t.add_lot("AAPL", 50, 150.0, date(2024, 1, 1))  # gain at 180
        result = t.sell("AAPL", 50, 180.0, date(2025, 3, 1), method="TaxOptimal")
        # Should sell the losing lot first
        assert result.cost_basis == pytest.approx(10000.0)  # 50 * 200
        assert result.realized_gain == pytest.approx(-1000.0)

    def test_sell_insufficient_shares(self):
        t = TaxLotTracker()
        t.add_lot("AAPL", 10, 150.0, date(2024, 1, 1))
        with pytest.raises(ValueError, match="Insufficient"):
            t.sell("AAPL", 20, 180.0, date(2025, 1, 1))

    def test_unrealized_gains(self):
        t = TaxLotTracker()
        t.add_lot("AAPL", 100, 150.0, date(2024, 1, 1))
        t.add_lot("GOOG", 50, 100.0, date(2024, 1, 1))
        result = t.unrealized_gains({"AAPL": 160.0, "GOOG": 90.0})
        assert result["AAPL"]["unrealized_gain"] == pytest.approx(1000.0)
        assert result["GOOG"]["unrealized_gain"] == pytest.approx(-500.0)
        assert result["total"]["unrealized_gain"] == pytest.approx(500.0)

    def test_tax_loss_harvest(self):
        t = TaxLotTracker()
        t.add_lot("AAPL", 100, 150.0, date(2024, 1, 1))
        t.add_lot("GOOG", 50, 100.0, date(2024, 1, 1))
        candidates = t.tax_loss_harvest({"AAPL": 140.0, "GOOG": 110.0}, threshold=0)
        assert len(candidates) == 1
        assert candidates[0].symbol == "AAPL"
        assert candidates[0].unrealized_loss < 0

    def test_tax_loss_harvest_threshold(self):
        t = TaxLotTracker()
        t.add_lot("AAPL", 100, 150.0, date(2024, 1, 1))
        # Loss = -500, threshold = 600 → not included
        candidates = t.tax_loss_harvest({"AAPL": 145.0}, threshold=600)
        assert len(candidates) == 0

    def test_add_lot_invalid(self):
        t = TaxLotTracker()
        with pytest.raises(ValueError):
            t.add_lot("AAPL", -10, 150.0, date(2024, 1, 1))

    def test_sell_no_lots(self):
        t = TaxLotTracker()
        with pytest.raises(ValueError):
            t.sell("AAPL", 10, 150.0, date(2025, 1, 1))


# ===========================================================================
#  4. Performance Attribution
# ===========================================================================

class TestPerformanceAttribution:
    """Tests for PerformanceAttribution (10 tests)."""

    def _sample_sectors(self):
        portfolio = [
            SectorAllocation("Tech", 0.40, 0.12),
            SectorAllocation("Health", 0.30, 0.08),
            SectorAllocation("Finance", 0.30, 0.05),
        ]
        benchmark = [
            SectorAllocation("Tech", 0.35, 0.10),
            SectorAllocation("Health", 0.35, 0.07),
            SectorAllocation("Finance", 0.30, 0.04),
        ]
        return portfolio, benchmark

    def test_brinson_active_return(self):
        pa = PerformanceAttribution()
        p, b = self._sample_sectors()
        result = pa.brinson_fachler(p, b)
        port_ret = sum(s.weight * s.ret for s in p)
        bench_ret = sum(s.weight * s.ret for s in b)
        assert result["active_return"] == pytest.approx(port_ret - bench_ret, abs=1e-6)

    def test_brinson_decomposition_sums(self):
        pa = PerformanceAttribution()
        p, b = self._sample_sectors()
        result = pa.brinson_fachler(p, b)
        total = result["total_allocation"] + result["total_selection"] + result["total_interaction"]
        assert total == pytest.approx(result["active_return"], abs=1e-6)

    def test_brinson_sectors_present(self):
        pa = PerformanceAttribution()
        p, b = self._sample_sectors()
        result = pa.brinson_fachler(p, b)
        assert "Tech" in result["sectors"]
        assert "allocation" in result["sectors"]["Tech"]

    def test_brinson_identical_portfolios(self):
        pa = PerformanceAttribution()
        p, _ = self._sample_sectors()
        result = pa.brinson_fachler(p, p)
        assert abs(result["active_return"]) < 1e-8

    def test_factor_attribution_basic(self):
        pa = PerformanceAttribution()
        rng = random.Random(42)
        market = [rng.gauss(0, 0.01) for _ in range(100)]
        returns = [0.001 + 1.2 * m + rng.gauss(0, 0.002) for m in market]
        result = pa.factor_attribution(returns, {"market": market})
        assert result["factors"]["market"]["beta"] == pytest.approx(1.2, abs=0.2)
        assert result["r_squared"] > 0.5

    def test_factor_attribution_insufficient_data(self):
        pa = PerformanceAttribution()
        result = pa.factor_attribution([0.01], {"mkt": [0.005]})
        assert "error" in result

    def test_risk_attribution_sums_to_vol(self):
        pa = PerformanceAttribution()
        weights = {"A": 0.5, "B": 0.5}
        cov = {"A": {"A": 0.04, "B": 0.01}, "B": {"A": 0.01, "B": 0.09}}
        result = pa.risk_attribution(weights, cov)
        total_crc = sum(a["risk_contribution"] for a in result["assets"].values())
        assert total_crc == pytest.approx(result["portfolio_volatility"], abs=0.001)

    def test_risk_attribution_pct_sums_to_one(self):
        pa = PerformanceAttribution()
        weights = {"A": 0.6, "B": 0.4}
        cov = {"A": {"A": 0.04, "B": 0.01}, "B": {"A": 0.01, "B": 0.09}}
        result = pa.risk_attribution(weights, cov)
        total_pct = sum(a["pct_contribution"] for a in result["assets"].values())
        assert total_pct == pytest.approx(1.0, abs=0.01)

    def test_generate_report_string(self):
        pa = PerformanceAttribution()
        p, b = self._sample_sectors()
        brinson = pa.brinson_fachler(p, b)
        report = pa.generate_report(brinson_result=brinson)
        assert "PERFORMANCE ATTRIBUTION REPORT" in report
        assert "Tech" in report

    def test_generate_report_all_sections(self):
        pa = PerformanceAttribution()
        p, b = self._sample_sectors()
        brinson = pa.brinson_fachler(p, b)
        weights = {"A": 0.5, "B": 0.5}
        cov = {"A": {"A": 0.04, "B": 0.01}, "B": {"A": 0.01, "B": 0.09}}
        risk = pa.risk_attribution(weights, cov)
        report = pa.generate_report(brinson_result=brinson, risk_result=risk)
        assert "Brinson" in report
        assert "Risk Attribution" in report


# ===========================================================================
#  5. Integration / edge cases
# ===========================================================================

class TestPortfolioIntegration:
    """Cross-module and edge-case tests (5 tests)."""

    def test_optimizer_single_asset(self):
        ret = {"SPY": [0.001] * 50}
        result = PortfolioOptimizer.min_variance(ret)
        assert result["weights"]["SPY"] == pytest.approx(1.0, abs=0.01)

    def test_cov_matrix_helper(self):
        ret = {"A": [0.01, 0.02, -0.01], "B": [0.02, 0.01, 0.0]}
        tickers, cov = _cov_matrix(ret)
        assert len(tickers) == 2
        assert len(cov) == 2
        assert cov[0][1] == cov[1][0]  # symmetric

    def test_mean_helper(self):
        assert _mean([1, 2, 3]) == pytest.approx(2.0)
        assert _mean([]) == 0.0

    def test_rebalancer_and_optimizer_together(self):
        ret = _fake_returns()
        opt = PortfolioOptimizer.max_sharpe(ret)
        r = Rebalancer(opt["weights"], threshold=0.05)
        # Simulate drifted weights
        drifted = {k: v + 0.1 for k, v in opt["weights"].items()}
        total = sum(drifted.values())
        drifted = {k: v / total for k, v in drifted.items()}
        result = r.check_drift(drifted)
        assert "max_drift" in result

    def test_tax_tracker_partial_sell(self):
        t = TaxLotTracker()
        t.add_lot("AAPL", 100, 150.0, date(2024, 1, 1))
        result = t.sell("AAPL", 30, 180.0, date(2025, 6, 1))
        assert result.shares_sold == pytest.approx(30.0)
        remaining = t.get_lots("AAPL")
        assert sum(l.shares for l in remaining) == pytest.approx(70.0)
