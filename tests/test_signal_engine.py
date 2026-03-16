"""Tests for SignalEngineV7 — regime detection, signal generation, edge cases."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from agents.signal_engine_v7 import SignalEngineV7, MarketRegime, SignalResult
from tests.conftest import (
    make_prices, make_bull_prices, make_bear_prices,
    make_crash_prices, make_ranging_prices, make_volatile_prices,
)


@pytest.fixture
def engine():
    return SignalEngineV7()


class TestRegimeDetection:
    def test_bull_regime_detected(self, engine):
        prices = make_bull_prices(300)
        sig = engine.generate_signal(prices)
        assert sig.regime in (MarketRegime.BULL, MarketRegime.STRONG_BULL)

    def test_bear_regime_detected(self, engine):
        prices = make_bear_prices(300)
        sig = engine.generate_signal(prices)
        assert sig.regime in (MarketRegime.BEAR, MarketRegime.STRONG_BEAR, MarketRegime.CRASH)

    def test_crash_regime_detected(self, engine):
        prices = make_crash_prices(300)
        sig = engine.generate_signal(prices)
        assert sig.regime in (MarketRegime.BEAR, MarketRegime.STRONG_BEAR, MarketRegime.CRASH)

    def test_ranging_regime_detected(self, engine):
        prices = make_ranging_prices(300, seed=99)
        sig = engine.generate_signal(prices)
        assert sig.regime in (MarketRegime.RANGING, MarketRegime.VOLATILE, MarketRegime.BULL, MarketRegime.BEAR)


class TestSignalGeneration:
    def test_signal_is_valid_type(self, engine):
        prices = make_prices(n=200)
        sig = engine.generate_signal(prices)
        assert sig.signal in ("buy", "strong_buy", "sell", "hold")

    def test_confidence_range(self, engine):
        prices = make_bull_prices(200)
        sig = engine.generate_signal(prices)
        assert 0.0 <= sig.confidence <= 1.0

    def test_position_size_range(self, engine):
        prices = make_bull_prices(200)
        sig = engine.generate_signal(prices)
        assert 0.0 <= sig.position_size <= 1.0

    def test_stop_loss_below_price(self, engine):
        prices = make_bull_prices(200)
        sig = engine.generate_signal(prices)
        if sig.signal in ("buy", "strong_buy") and sig.stop_loss > 0:
            assert sig.stop_loss < prices[-1]

    def test_take_profit_above_price(self, engine):
        prices = make_bull_prices(200)
        sig = engine.generate_signal(prices)
        if sig.signal in ("buy", "strong_buy") and sig.take_profit > 0:
            assert sig.take_profit > prices[-1]

    def test_trailing_stop_positive(self, engine):
        prices = make_bull_prices(200)
        sig = engine.generate_signal(prices)
        assert sig.trailing_stop_pct >= 0

    def test_factors_dict_present(self, engine):
        prices = make_bull_prices(200)
        sig = engine.generate_signal(prices)
        assert isinstance(sig.factors, dict)


class TestEdgeCases:
    def test_short_series_returns_hold(self, engine):
        """Less than 20 bars should return hold."""
        sig = engine.generate_signal([100.0] * 10)
        assert sig.signal == "hold"

    def test_single_price(self, engine):
        sig = engine.generate_signal([100.0])
        assert sig.signal == "hold"

    def test_flat_prices(self, engine):
        """Perfectly flat prices should not crash."""
        sig = engine.generate_signal([100.0] * 200)
        assert sig.signal in ("buy", "strong_buy", "sell", "hold")

    def test_with_volumes(self, engine):
        prices = make_bull_prices(200)
        volumes = [1_000_000 + i * 100 for i in range(200)]
        sig = engine.generate_signal(prices, volumes=volumes)
        assert isinstance(sig, SignalResult)

    def test_with_existing_position(self, engine):
        prices = make_bull_prices(200)
        sig = engine.generate_signal(prices, current_position=0.5)
        assert isinstance(sig, SignalResult)

    def test_deterministic_output(self, engine):
        """Same input → same output."""
        prices = make_bull_prices(200, seed=123)
        sig1 = engine.generate_signal(prices)
        engine2 = SignalEngineV7()
        sig2 = engine2.generate_signal(prices)
        assert sig1.signal == sig2.signal
        assert sig1.confidence == sig2.confidence
