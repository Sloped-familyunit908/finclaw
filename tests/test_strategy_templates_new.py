"""Tests for Issue #5: New built-in strategy templates.

Tests for additional strategy templates:
- VWAP Strategy (volume-weighted average price reversion)
- RSI Divergence Strategy (RSI/price divergence detection)
- Ichimoku Cloud Strategy (Japanese cloud-based trend following)
- Momentum Rotation Strategy (cross-asset momentum rotation)
"""

import math

import pytest

from src.strategies.library.base import Strategy, StrategySignal, StrategyMeta


# ── VWAP Strategy ──────────────────────────────────────────────

class TestVWAPStrategy:
    def _make_data(self, n=50, base_price=100, volume=1000):
        """Generate OHLCV data."""
        data = []
        for i in range(n):
            p = base_price + (i % 10) - 5
            data.append({
                "open": p - 0.5,
                "high": p + 1,
                "low": p - 1,
                "close": p,
                "volume": volume + (i * 10),
            })
        return data

    def test_import(self):
        from src.strategies.library.vwap import VWAPStrategy
        assert issubclass(VWAPStrategy, Strategy)

    def test_meta(self):
        from src.strategies.library.vwap import VWAPStrategy
        meta = VWAPStrategy.meta()
        assert isinstance(meta, StrategyMeta)
        assert "vwap" in meta.slug.lower()
        assert meta.category in ("stock", "universal", "crypto")

    def test_generate_signals(self):
        from src.strategies.library.vwap import VWAPStrategy
        strategy = VWAPStrategy()
        data = self._make_data()
        signals = strategy.generate_signals(data)
        assert len(signals) == len(data)
        assert all(isinstance(s, StrategySignal) for s in signals)

    def test_signals_contain_valid_actions(self):
        from src.strategies.library.vwap import VWAPStrategy
        strategy = VWAPStrategy()
        data = self._make_data()
        signals = strategy.generate_signals(data)
        valid_actions = {"buy", "sell", "hold"}
        for s in signals:
            assert s.action in valid_actions

    def test_confidence_range(self):
        from src.strategies.library.vwap import VWAPStrategy
        strategy = VWAPStrategy()
        data = self._make_data()
        signals = strategy.generate_signals(data)
        for s in signals:
            assert 0.0 <= s.confidence <= 1.0

    def test_backtest_returns_results(self):
        from src.strategies.library.vwap import VWAPStrategy
        strategy = VWAPStrategy()
        data = self._make_data(100)
        result = strategy.backtest(data)
        assert "total_return" in result
        assert "sharpe_ratio" in result
        assert "max_drawdown" in result

    def test_custom_parameters(self):
        from src.strategies.library.vwap import VWAPStrategy
        strategy = VWAPStrategy(lookback=10, std_dev=1.5)
        data = self._make_data()
        signals = strategy.generate_signals(data)
        assert len(signals) == len(data)


# ── RSI Divergence Strategy ─────────────────────────────────────

class TestRSIDivergenceStrategy:
    def _make_data(self, n=50):
        """Data with potential divergences."""
        data = []
        for i in range(n):
            # Create a pattern with higher close but lower momentum
            if i < 25:
                p = 100 + i * 0.5
            else:
                p = 112 + (i - 25) * 0.3
            data.append({
                "open": p - 0.3,
                "high": p + 0.5,
                "low": p - 0.5,
                "close": p,
                "volume": 1000,
            })
        return data

    def test_import(self):
        from src.strategies.library.rsi_divergence import RSIDivergenceStrategy
        assert issubclass(RSIDivergenceStrategy, Strategy)

    def test_meta(self):
        from src.strategies.library.rsi_divergence import RSIDivergenceStrategy
        meta = RSIDivergenceStrategy.meta()
        assert isinstance(meta, StrategyMeta)
        assert "rsi" in meta.slug.lower() or "divergence" in meta.slug.lower()

    def test_generate_signals(self):
        from src.strategies.library.rsi_divergence import RSIDivergenceStrategy
        strategy = RSIDivergenceStrategy()
        data = self._make_data()
        signals = strategy.generate_signals(data)
        assert len(signals) == len(data)
        assert all(isinstance(s, StrategySignal) for s in signals)

    def test_signals_valid_actions(self):
        from src.strategies.library.rsi_divergence import RSIDivergenceStrategy
        strategy = RSIDivergenceStrategy()
        data = self._make_data()
        signals = strategy.generate_signals(data)
        valid_actions = {"buy", "sell", "hold"}
        for s in signals:
            assert s.action in valid_actions

    def test_backtest(self):
        from src.strategies.library.rsi_divergence import RSIDivergenceStrategy
        strategy = RSIDivergenceStrategy()
        data = self._make_data(100)
        result = strategy.backtest(data)
        assert "total_return" in result
        assert "num_trades" in result

    def test_custom_rsi_period(self):
        from src.strategies.library.rsi_divergence import RSIDivergenceStrategy
        strategy = RSIDivergenceStrategy(rsi_period=7, lookback=5)
        data = self._make_data()
        signals = strategy.generate_signals(data)
        assert len(signals) == len(data)


# ── Ichimoku Cloud Strategy ─────────────────────────────────────

class TestIchimokuStrategy:
    def _make_data(self, n=80):
        """Generate enough data for Ichimoku (needs 52+ bars)."""
        data = []
        for i in range(n):
            # Trending up
            base = 100 + i * 0.5
            data.append({
                "open": base - 0.3,
                "high": base + 1.0,
                "low": base - 1.0,
                "close": base + 0.2,
                "volume": 1000 + i * 5,
            })
        return data

    def test_import(self):
        from src.strategies.library.ichimoku import IchimokuStrategy
        assert issubclass(IchimokuStrategy, Strategy)

    def test_meta(self):
        from src.strategies.library.ichimoku import IchimokuStrategy
        meta = IchimokuStrategy.meta()
        assert isinstance(meta, StrategyMeta)
        assert "ichimoku" in meta.slug.lower()

    def test_generate_signals(self):
        from src.strategies.library.ichimoku import IchimokuStrategy
        strategy = IchimokuStrategy()
        data = self._make_data()
        signals = strategy.generate_signals(data)
        assert len(signals) == len(data)
        assert all(isinstance(s, StrategySignal) for s in signals)

    def test_signals_valid_actions(self):
        from src.strategies.library.ichimoku import IchimokuStrategy
        strategy = IchimokuStrategy()
        data = self._make_data()
        signals = strategy.generate_signals(data)
        valid_actions = {"buy", "sell", "hold"}
        for s in signals:
            assert s.action in valid_actions

    def test_backtest(self):
        from src.strategies.library.ichimoku import IchimokuStrategy
        strategy = IchimokuStrategy()
        data = self._make_data(120)
        result = strategy.backtest(data)
        assert "total_return" in result
        assert "equity_curve" in result

    def test_requires_enough_data(self):
        from src.strategies.library.ichimoku import IchimokuStrategy
        strategy = IchimokuStrategy()
        # With too little data, all signals should be hold
        data = self._make_data(10)
        signals = strategy.generate_signals(data)
        assert all(s.action == "hold" for s in signals)


# ── Momentum Rotation Strategy ──────────────────────────────────

class TestMomentumRotationStrategy:
    def _make_data(self, n=50):
        data = []
        for i in range(n):
            p = 100 + i * 0.3
            data.append({
                "open": p - 0.2,
                "high": p + 0.5,
                "low": p - 0.5,
                "close": p,
                "volume": 1000,
            })
        return data

    def test_import(self):
        from src.strategies.library.momentum_rotation import MomentumRotationStrategy
        assert issubclass(MomentumRotationStrategy, Strategy)

    def test_meta(self):
        from src.strategies.library.momentum_rotation import MomentumRotationStrategy
        meta = MomentumRotationStrategy.meta()
        assert isinstance(meta, StrategyMeta)
        assert "momentum" in meta.slug.lower() or "rotation" in meta.slug.lower()

    def test_generate_signals(self):
        from src.strategies.library.momentum_rotation import MomentumRotationStrategy
        strategy = MomentumRotationStrategy()
        data = self._make_data()
        signals = strategy.generate_signals(data)
        assert len(signals) == len(data)
        assert all(isinstance(s, StrategySignal) for s in signals)

    def test_backtest(self):
        from src.strategies.library.momentum_rotation import MomentumRotationStrategy
        strategy = MomentumRotationStrategy()
        data = self._make_data(100)
        result = strategy.backtest(data)
        assert "total_return" in result

    def test_custom_lookback(self):
        from src.strategies.library.momentum_rotation import MomentumRotationStrategy
        strategy = MomentumRotationStrategy(lookback=10, rebalance_period=5)
        data = self._make_data()
        signals = strategy.generate_signals(data)
        assert len(signals) == len(data)


# ── Registry ───────────────────────────────────────────────────

class TestStrategyRegistryExpanded:
    def test_new_strategies_in_registry(self):
        from src.strategies.library import STRATEGY_REGISTRY
        assert "vwap" in STRATEGY_REGISTRY
        assert "rsi-divergence" in STRATEGY_REGISTRY
        assert "ichimoku" in STRATEGY_REGISTRY
        assert "momentum-rotation" in STRATEGY_REGISTRY

    def test_get_strategy_vwap(self):
        from src.strategies.library import get_strategy
        cls = get_strategy("vwap")
        assert cls is not None

    def test_get_strategy_rsi_divergence(self):
        from src.strategies.library import get_strategy
        cls = get_strategy("rsi-divergence")
        assert cls is not None

    def test_get_strategy_ichimoku(self):
        from src.strategies.library import get_strategy
        cls = get_strategy("ichimoku")
        assert cls is not None

    def test_get_strategy_momentum_rotation(self):
        from src.strategies.library import get_strategy
        cls = get_strategy("momentum-rotation")
        assert cls is not None

    def test_list_strategies_includes_new(self):
        from src.strategies.library import list_strategies
        strategies = list_strategies()
        slugs = [s.slug for s in strategies]
        assert "vwap" in slugs
        assert "rsi-divergence" in slugs
        assert "ichimoku" in slugs
        assert "momentum-rotation" in slugs

    def test_total_strategy_count(self):
        from src.strategies.library import STRATEGY_REGISTRY
        # Was 11, now should be 15
        assert len(STRATEGY_REGISTRY) >= 15
