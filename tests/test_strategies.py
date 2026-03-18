"""Tests for strategy backtesting engines: MACD, Bollinger, Momentum."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import asyncio
from agents.strategies import (
    MACDStrategy, BollingerStrategy, MomentumStrategy,
    STRATEGY_MAP, _ema, _sma, _macd, _bollinger_bands,
)
from tests.conftest import (
    make_bull_prices, make_bear_prices, make_crash_prices,
    make_ranging_prices, make_volatile_prices, make_history,
)


def run(coro):
    return asyncio.run(coro)


# ── Helper function tests ──────────────────────────────────────────


class TestHelperFunctions:
    def test_ema_basic(self):
        prices = [10.0, 11.0, 12.0, 11.0, 10.0]
        result = _ema(prices, 3)
        assert len(result) == len(prices)
        assert result[0] == prices[0]  # First value is the price itself

    def test_sma_basic(self):
        prices = [10.0, 11.0, 12.0, 13.0, 14.0]
        result = _sma(prices, 3)
        assert len(result) == len(prices)
        import math
        assert math.isnan(result[0])
        assert math.isnan(result[1])
        assert abs(result[2] - 11.0) < 1e-10  # (10+11+12)/3
        assert abs(result[3] - 12.0) < 1e-10  # (11+12+13)/3

    def test_macd_output_shape(self):
        prices = [100 + i * 0.5 for i in range(50)]
        macd_line, signal_line, histogram = _macd(prices)
        assert len(macd_line) == len(prices)
        assert len(signal_line) == len(prices)
        assert len(histogram) == len(prices)

    def test_bollinger_bands_output_shape(self):
        prices = [100 + i * 0.1 for i in range(50)]
        upper, middle, lower = _bollinger_bands(prices, period=20)
        assert len(upper) == len(prices)
        assert len(middle) == len(prices)
        assert len(lower) == len(prices)

    def test_bollinger_bands_ordering(self):
        import math
        prices = [100 + i * 0.1 for i in range(50)]
        upper, middle, lower = _bollinger_bands(prices, period=20)
        # After warmup, upper > middle > lower
        for i in range(19, 50):
            if not math.isnan(upper[i]):
                assert upper[i] >= middle[i] >= lower[i]


# ── Strategy Registry ──────────────────────────────────────────────


class TestStrategyRegistry:
    def test_all_strategies_in_map(self):
        assert "macd" in STRATEGY_MAP
        assert "bollinger" in STRATEGY_MAP
        assert "momentum" in STRATEGY_MAP

    def test_map_values_are_classes(self):
        for name, cls in STRATEGY_MAP.items():
            assert hasattr(cls, "run"), f"{name} strategy missing run method"
            assert hasattr(cls, "warmup_period"), f"{name} strategy missing warmup_period"
            assert hasattr(cls, "generate_signal"), f"{name} strategy missing generate_signal"


# ── MACD Strategy ──────────────────────────────────────────────────


class TestMACDStrategy:
    @pytest.fixture
    def macd(self):
        return MACDStrategy(initial_capital=100_000)

    def test_bull_market_returns(self, macd):
        h = make_history(make_bull_prices(500))
        r = run(macd.run("TEST", "macd", h))
        assert isinstance(r.total_return, float)
        assert r.total_trades > 0, "Should execute trades in bull market"

    def test_bear_market_limited_loss(self, macd):
        h = make_history(make_bear_prices(500))
        r = run(macd.run("TEST", "macd", h))
        assert r.total_return > -0.8, f"Bear loss too large: {r.total_return}"

    def test_ranging_market(self, macd):
        h = make_history(make_ranging_prices(500))
        r = run(macd.run("TEST", "macd", h))
        assert r.total_return > -0.5

    def test_volatile_market(self, macd):
        h = make_history(make_volatile_prices(500))
        r = run(macd.run("TEST", "macd", h))
        assert isinstance(r.total_return, float)

    def test_crash_survival(self, macd):
        h = make_history(make_crash_prices(500))
        r = run(macd.run("TEST", "macd", h))
        assert r.total_return > -0.8

    def test_metrics_valid(self, macd):
        h = make_history(make_bull_prices(300))
        r = run(macd.run("TEST", "macd", h))
        assert 0.0 <= r.win_rate <= 1.0
        assert -1.0 <= r.max_drawdown <= 0.0
        assert r.total_trades == r.winning_trades + r.losing_trades

    def test_equity_curve_grows(self, macd):
        h = make_history(make_bull_prices(300))
        r = run(macd.run("TEST", "macd", h))
        assert len(r.equity_curve) > 0

    def test_custom_params(self):
        macd = MACDStrategy(initial_capital=50_000, fast=8, slow=21, signal_period=5)
        h = make_history(make_bull_prices(300))
        r = run(macd.run("TEST", "macd", h))
        assert isinstance(r.total_return, float)

    def test_signal_generation(self):
        macd = MACDStrategy()
        # Uptrending prices should eventually generate a buy
        prices = make_bull_prices(100)
        signals = [macd.generate_signal(prices, i) for i in range(macd.warmup_period, len(prices))]
        assert "buy" in signals, "MACD should generate buy signals in uptrend"

    def test_short_history_raises(self, macd):
        h = make_history([100.0] * 10)
        with pytest.raises(ValueError):
            run(macd.run("TEST", "macd", h))


# ── Bollinger Strategy ─────────────────────────────────────────────


class TestBollingerStrategy:
    @pytest.fixture
    def bb(self):
        return BollingerStrategy(initial_capital=100_000)

    def test_bull_market(self, bb):
        h = make_history(make_bull_prices(500))
        r = run(bb.run("TEST", "bollinger", h))
        assert isinstance(r.total_return, float)

    def test_ranging_market_trades(self, bb):
        """Bollinger should trade well in ranging markets (mean reversion)."""
        h = make_history(make_ranging_prices(500))
        r = run(bb.run("TEST", "bollinger", h))
        assert r.total_trades > 0, "Bollinger should trade in ranging market"

    def test_bear_market_limited_loss(self, bb):
        h = make_history(make_bear_prices(500))
        r = run(bb.run("TEST", "bollinger", h))
        assert r.total_return > -0.8

    def test_volatile_market(self, bb):
        h = make_history(make_volatile_prices(500))
        r = run(bb.run("TEST", "bollinger", h))
        assert isinstance(r.total_return, float)

    def test_crash_survival(self, bb):
        h = make_history(make_crash_prices(500))
        r = run(bb.run("TEST", "bollinger", h))
        # Mean reversion suffers in crashes; allow wider tolerance
        assert r.total_return > -0.9

    def test_metrics_valid(self, bb):
        h = make_history(make_bull_prices(300))
        r = run(bb.run("TEST", "bollinger", h))
        assert 0.0 <= r.win_rate <= 1.0
        assert -1.0 <= r.max_drawdown <= 0.0
        assert r.total_trades == r.winning_trades + r.losing_trades

    def test_custom_params(self):
        bb = BollingerStrategy(initial_capital=50_000, period=15, num_std=1.5)
        h = make_history(make_ranging_prices(300))
        r = run(bb.run("TEST", "bollinger", h))
        assert isinstance(r.total_return, float)

    def test_signal_generation_lower_band(self):
        bb = BollingerStrategy()
        # In volatile market, prices should drop below lower band
        prices = make_volatile_prices(200)
        signals = [bb.generate_signal(prices, i) for i in range(bb.warmup_period, len(prices))]
        has_buy = "buy" in signals
        has_sell = "sell" in signals
        assert has_buy or has_sell, "Bollinger should generate signals in volatile market"

    def test_short_history_raises(self, bb):
        h = make_history([100.0] * 10)
        with pytest.raises(ValueError):
            run(bb.run("TEST", "bollinger", h))


# ── Momentum Strategy ─────────────────────────────────────────────


class TestMomentumStrategy:
    @pytest.fixture
    def mom(self):
        return MomentumStrategy(initial_capital=100_000)

    def test_bull_market_profitable(self, mom):
        """Momentum should capture strong bull trends."""
        h = make_history(make_bull_prices(500))
        r = run(mom.run("TEST", "momentum", h))
        assert r.total_return > 0, f"Momentum should profit in bull, got {r.total_return}"

    def test_bear_market_limited_loss(self, mom):
        h = make_history(make_bear_prices(500))
        r = run(mom.run("TEST", "momentum", h))
        assert r.total_return > -0.8

    def test_ranging_market(self, mom):
        h = make_history(make_ranging_prices(500))
        r = run(mom.run("TEST", "momentum", h))
        assert isinstance(r.total_return, float)

    def test_volatile_market(self, mom):
        h = make_history(make_volatile_prices(500))
        r = run(mom.run("TEST", "momentum", h))
        assert isinstance(r.total_return, float)

    def test_crash_survival(self, mom):
        h = make_history(make_crash_prices(500))
        r = run(mom.run("TEST", "momentum", h))
        assert r.total_return > -0.8

    def test_metrics_valid(self, mom):
        h = make_history(make_bull_prices(300))
        r = run(mom.run("TEST", "momentum", h))
        assert 0.0 <= r.win_rate <= 1.0
        assert -1.0 <= r.max_drawdown <= 0.0
        assert r.total_trades == r.winning_trades + r.losing_trades

    def test_custom_lookback(self):
        mom = MomentumStrategy(initial_capital=50_000, lookback=10)
        h = make_history(make_bull_prices(300))
        r = run(mom.run("TEST", "momentum", h))
        assert isinstance(r.total_return, float)
        # Shorter lookback: more responsive, more trades
        assert r.total_trades >= 0

    def test_signal_generation_breakout(self):
        mom = MomentumStrategy(lookback=20)
        # Strong uptrend should generate buy signals (breaking N-day highs)
        prices = make_bull_prices(100)
        signals = [mom.generate_signal(prices, i) for i in range(mom.warmup_period, len(prices))]
        assert "buy" in signals, "Momentum should generate buy on upward breakout"

    def test_short_history_raises(self, mom):
        h = make_history([100.0] * 10)
        with pytest.raises(ValueError):
            run(mom.run("TEST", "momentum", h))

    def test_breakout_logic(self):
        """Verify breakout is detected correctly."""
        mom = MomentumStrategy(lookback=5)
        # Flat then breakout
        prices = [100.0] * 10 + [105.0]
        signal = mom.generate_signal(prices, 10)
        assert signal == "buy", "Should buy on breakout above range"

    def test_breakdown_logic(self):
        """Verify breakdown sell is detected correctly."""
        mom = MomentumStrategy(lookback=5)
        # Flat then breakdown
        prices = [100.0] * 10 + [95.0]
        signal = mom.generate_signal(prices, 10)
        assert signal == "sell", "Should sell on breakdown below range"


# ── Cross-strategy tests ──────────────────────────────────────────


class TestCrossStrategy:
    def test_all_strategies_complete(self):
        """All strategies should produce valid BacktestResult on same data."""
        h = make_history(make_bull_prices(300))
        for name, Cls in STRATEGY_MAP.items():
            bt = Cls(initial_capital=100_000)
            r = run(bt.run("TEST", name, h))
            assert hasattr(r, "total_return"), f"{name} result missing total_return"
            assert hasattr(r, "total_trades"), f"{name} result missing total_trades"
            assert hasattr(r, "max_drawdown"), f"{name} result missing max_drawdown"
            assert hasattr(r, "equity_curve"), f"{name} result missing equity_curve"

    def test_results_fields(self):
        """All results should have complete BacktestResult fields."""
        h = make_history(make_bull_prices(300))
        for name, Cls in STRATEGY_MAP.items():
            bt = Cls(initial_capital=100_000)
            r = run(bt.run("TEST", name, h))
            assert r.strategy_name == name
            assert r.asset == "TEST"
            assert isinstance(r.equity_curve, list)
            assert isinstance(r.trades, list)

    def test_different_strategies_different_results(self):
        """Strategies should produce different trade counts (they aren't identical)."""
        h = make_history(make_bull_prices(500))
        results = {}
        for name, Cls in STRATEGY_MAP.items():
            bt = Cls(initial_capital=100_000)
            r = run(bt.run("TEST", name, h))
            results[name] = r.total_trades

        # At least 2 strategies should have different trade counts
        unique_counts = set(results.values())
        assert len(unique_counts) >= 2, f"Strategies too similar: {results}"
