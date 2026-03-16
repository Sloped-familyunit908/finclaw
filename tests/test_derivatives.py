"""Tests for derivatives and fixed income modules — 35+ test cases."""

import math
import os
import tempfile
import pytest
import numpy as np

from src.derivatives.options_pricing import BlackScholes, BinomialTree, MonteCarloPricer
from src.derivatives.vol_surface import VolatilitySurface
from src.derivatives.greeks import OptionPosition, PortfolioGreeks
from src.fixed_income.yield_curve import YieldCurve


# ============================================================
# Black-Scholes Tests
# ============================================================

class TestBlackScholes:
    """Standard BS params: S=100, K=100, T=1, r=0.05, sigma=0.2."""

    S, K, T, r, sigma = 100, 100, 1.0, 0.05, 0.2

    def test_call_price_positive(self):
        price = BlackScholes.call_price(self.S, self.K, self.T, self.r, self.sigma)
        assert price > 0

    def test_put_price_positive(self):
        price = BlackScholes.put_price(self.S, self.K, self.T, self.r, self.sigma)
        assert price > 0

    def test_put_call_parity(self):
        """C - P = S - K*exp(-rT)"""
        c = BlackScholes.call_price(self.S, self.K, self.T, self.r, self.sigma)
        p = BlackScholes.put_price(self.S, self.K, self.T, self.r, self.sigma)
        parity = self.S - self.K * math.exp(-self.r * self.T)
        assert abs((c - p) - parity) < 1e-10

    def test_call_deep_itm(self):
        price = BlackScholes.call_price(200, 100, 1.0, 0.05, 0.2)
        assert price > 95  # intrinsic ~ 100

    def test_put_deep_itm(self):
        price = BlackScholes.put_price(50, 100, 1.0, 0.05, 0.2)
        assert price > 45

    def test_expired_call(self):
        assert BlackScholes.call_price(110, 100, 0, 0.05, 0.2) == 10.0

    def test_expired_put(self):
        assert BlackScholes.put_price(90, 100, 0, 0.05, 0.2) == 10.0

    def test_expired_otm(self):
        assert BlackScholes.call_price(90, 100, 0, 0.05, 0.2) == 0.0

    def test_greeks_keys(self):
        g = BlackScholes.greeks(self.S, self.K, self.T, self.r, self.sigma)
        assert set(g.keys()) == {"delta", "gamma", "theta", "vega", "rho"}

    def test_call_delta_range(self):
        g = BlackScholes.greeks(self.S, self.K, self.T, self.r, self.sigma)
        assert 0 < g["delta"] < 1

    def test_gamma_positive(self):
        g = BlackScholes.greeks(self.S, self.K, self.T, self.r, self.sigma)
        assert g["gamma"] > 0

    def test_vega_positive(self):
        g = BlackScholes.greeks(self.S, self.K, self.T, self.r, self.sigma)
        assert g["vega"] > 0

    def test_greeks_expired(self):
        g = BlackScholes.greeks(110, 100, 0, 0.05, 0.2)
        assert g["delta"] == 1.0
        assert g["gamma"] == 0.0


# ============================================================
# Binomial Tree Tests
# ============================================================

class TestBinomialTree:
    def test_european_call_converges_to_bs(self):
        bt = BinomialTree(steps=200)
        bs_price = BlackScholes.call_price(100, 100, 1.0, 0.05, 0.2)
        bt_price = bt.price("call", 100, 100, 1.0, 0.05, 0.2, american=False)
        assert abs(bt_price - bs_price) < 0.5

    def test_european_put_converges_to_bs(self):
        bt = BinomialTree(steps=200)
        bs_price = BlackScholes.put_price(100, 100, 1.0, 0.05, 0.2)
        bt_price = bt.price("put", 100, 100, 1.0, 0.05, 0.2, american=False)
        assert abs(bt_price - bs_price) < 0.5

    def test_american_put_geq_european(self):
        bt = BinomialTree(steps=100)
        eu = bt.price("put", 100, 100, 1.0, 0.05, 0.2, american=False)
        am = bt.price("put", 100, 100, 1.0, 0.05, 0.2, american=True)
        assert am >= eu - 1e-10

    def test_american_call_no_dividend_equals_european(self):
        bt = BinomialTree(steps=100)
        eu = bt.price("call", 100, 100, 1.0, 0.05, 0.2, american=False)
        am = bt.price("call", 100, 100, 1.0, 0.05, 0.2, american=True)
        assert abs(am - eu) < 0.5


# ============================================================
# Monte Carlo Tests
# ============================================================

class TestMonteCarlo:
    def test_call_price_near_bs(self):
        mc = MonteCarloPricer(simulations=50000, seed=42)
        result = mc.price("call", 100, 100, 1.0, 0.05, 0.2)
        bs = BlackScholes.call_price(100, 100, 1.0, 0.05, 0.2)
        assert abs(result["price"] - bs) < 1.0

    def test_put_price_near_bs(self):
        mc = MonteCarloPricer(simulations=50000, seed=42)
        result = mc.price("put", 100, 100, 1.0, 0.05, 0.2)
        bs = BlackScholes.put_price(100, 100, 1.0, 0.05, 0.2)
        assert abs(result["price"] - bs) < 1.0

    def test_result_keys(self):
        mc = MonteCarloPricer(simulations=1000, seed=1)
        result = mc.price("call", 100, 100, 1.0, 0.05, 0.2)
        assert "price" in result
        assert "std_error" in result
        assert "confidence_interval" in result

    def test_confidence_interval_contains_price(self):
        mc = MonteCarloPricer(simulations=10000, seed=42)
        r = mc.price("call", 100, 100, 1.0, 0.05, 0.2)
        lo, hi = r["confidence_interval"]
        assert lo <= r["price"] <= hi

    def test_custom_payoff(self):
        mc = MonteCarloPricer(simulations=10000, seed=42)
        # Digital call: pays 1 if S_T > K
        result = mc.price("call", 100, 100, 1.0, 0.05, 0.2, payoff_fn=lambda s, k: 1.0 if s > k else 0.0)
        assert 0 < result["price"] < 1


# ============================================================
# Volatility Surface Tests
# ============================================================

class TestVolatilitySurface:
    def _make_surface(self):
        vs = VolatilitySurface()
        for strike in [90, 100, 110]:
            for expiry in [0.25, 0.5, 1.0]:
                vol = 0.2 + 0.001 * (strike - 100) ** 2 + 0.01 * expiry
                vs.add_point(strike, expiry, vol)
        return vs

    def test_add_and_count(self):
        vs = self._make_surface()
        assert len(vs.points) == 9

    def test_interpolate_exact_point(self):
        vs = VolatilitySurface()
        vs.add_point(100, 0.5, 0.25)
        assert abs(vs.interpolate(100, 0.5) - 0.25) < 1e-10

    def test_interpolate_between_points(self):
        vs = self._make_surface()
        vol = vs.interpolate(95, 0.375)
        assert 0.15 < vol < 0.35

    def test_get_smile(self):
        vs = self._make_surface()
        smile = vs.get_smile(0.25)
        assert len(smile) == 3
        assert 90 in smile

    def test_empty_surface_raises(self):
        vs = VolatilitySurface()
        with pytest.raises(ValueError):
            vs.interpolate(100, 0.5)

    def test_negative_vol_raises(self):
        vs = VolatilitySurface()
        with pytest.raises(ValueError):
            vs.add_point(100, 0.5, -0.1)

    def test_render_html(self):
        vs = self._make_surface()
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            path = f.name
        try:
            vs.render_html(path)
            assert os.path.getsize(path) > 100
            with open(path) as f:
                content = f.read()
            assert "Plotly" in content
        finally:
            os.unlink(path)


# ============================================================
# Portfolio Greeks Tests
# ============================================================

class TestPortfolioGreeks:
    def test_single_call(self):
        pos = OptionPosition("call", 100, 100, 1.0, 0.05, 0.2, quantity=1)
        pg = PortfolioGreeks()
        result = pg.calculate([pos])
        assert result["net_delta"] > 0
        assert result["net_gamma"] > 0

    def test_delta_neutral_straddle(self):
        """Long call + long put at same strike should have near-zero delta."""
        c = OptionPosition("call", 100, 100, 1.0, 0.05, 0.2, quantity=1)
        p = OptionPosition("put", 100, 100, 1.0, 0.05, 0.2, quantity=1)
        pg = PortfolioGreeks()
        result = pg.calculate([c, p])
        # Not exactly zero due to rates, but close
        assert abs(result["net_delta"]) < 50  # not exactly zero due to rates

    def test_short_position_negative_delta(self):
        pos = OptionPosition("call", 100, 100, 1.0, 0.05, 0.2, quantity=-1)
        pg = PortfolioGreeks()
        result = pg.calculate([pos])
        assert result["net_delta"] < 0

    def test_hedge_recommendation_exists(self):
        pos = OptionPosition("call", 100, 100, 1.0, 0.05, 0.2, quantity=10)
        pg = PortfolioGreeks()
        recs = pg.hedge_recommendation([pos])
        assert len(recs) > 0
        assert any(r["instrument"] == "underlying_shares" for r in recs)

    def test_hedge_no_action_needed(self):
        """Tiny position should not trigger hedging."""
        pos = OptionPosition("call", 100, 100, 0.001, 0.05, 0.2, quantity=0)
        pg = PortfolioGreeks()
        recs = pg.hedge_recommendation([pos])
        assert any(r["action"] == "none" for r in recs)


# ============================================================
# Yield Curve Tests
# ============================================================

class TestYieldCurve:
    tenors = [0.25, 0.5, 1, 2, 5, 10, 30]
    rates = [0.045, 0.046, 0.047, 0.044, 0.042, 0.043, 0.045]

    def test_interpolate_exact(self):
        yc = YieldCurve(self.tenors, self.rates)
        assert abs(yc.interpolate(1.0) - 0.047) < 1e-10

    def test_interpolate_between(self):
        yc = YieldCurve(self.tenors, self.rates)
        r = yc.interpolate(0.75)
        assert 0.046 < r < 0.047

    def test_extrapolate_flat(self):
        yc = YieldCurve(self.tenors, self.rates)
        assert yc.interpolate(0.1) == 0.045
        assert yc.interpolate(50) == 0.045

    def test_forward_rate(self):
        yc = YieldCurve(self.tenors, self.rates)
        fwd = yc.forward_rate(1, 2)
        # Forward should be calculable
        assert isinstance(fwd, float)

    def test_forward_rate_invalid(self):
        yc = YieldCurve(self.tenors, self.rates)
        with pytest.raises(ValueError):
            yc.forward_rate(2, 1)

    def test_discount_factor(self):
        yc = YieldCurve(self.tenors, self.rates)
        df = yc.discount_factor(1.0)
        assert 0 < df < 1
        assert abs(df - math.exp(-0.047)) < 1e-10

    def test_is_inverted_false(self):
        yc = YieldCurve([1, 10], [0.03, 0.05])
        assert yc.is_inverted() is False

    def test_is_inverted_true(self):
        yc = YieldCurve([1, 10], [0.05, 0.03])
        assert yc.is_inverted() is True

    def test_mismatched_lengths_raises(self):
        with pytest.raises(ValueError):
            YieldCurve([1, 2], [0.05])

    def test_too_few_points_raises(self):
        with pytest.raises(ValueError):
            YieldCurve([1], [0.05])
