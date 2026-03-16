"""Tests for SignalCombiner."""

import pytest
from src.strategies.signal_combiner import SignalCombiner


class MockStrategy:
    def __init__(self, signal, confidence=0.8):
        self._signal = signal
        self._confidence = confidence

    def generate_signal(self, data):
        return {'signal': self._signal, 'confidence': self._confidence}


class FailingStrategy:
    def generate_signal(self, data):
        raise RuntimeError("boom")


class TestSignalCombiner:
    def test_combine_equal_weights(self):
        strategies = [('A', MockStrategy(1.0)), ('B', MockStrategy(-1.0))]
        sc = SignalCombiner(strategies)
        result = sc.combine({})
        assert result['signal'] == 0.0

    def test_combine_all_bullish(self):
        strategies = [('A', MockStrategy(1.0)), ('B', MockStrategy(1.0))]
        sc = SignalCombiner(strategies)
        result = sc.combine({})
        assert result['signal'] == 1.0

    def test_combine_weighted(self):
        strategies = [('A', MockStrategy(1.0)), ('B', MockStrategy(-1.0))]
        sc = SignalCombiner(strategies, weights=[3, 1])
        result = sc.combine({})
        assert result['signal'] > 0  # A dominates

    def test_combine_contributing(self):
        strategies = [('A', MockStrategy(1.0)), ('B', MockStrategy(0.0)), ('C', MockStrategy(-1.0))]
        sc = SignalCombiner(strategies)
        result = sc.combine({})
        assert 'A' in result['contributing']
        assert 'C' in result['contributing']
        assert 'B' not in result['contributing']

    def test_combine_confidence(self):
        strategies = [('A', MockStrategy(1.0, 0.9)), ('B', MockStrategy(1.0, 0.5))]
        sc = SignalCombiner(strategies)
        result = sc.combine({})
        assert 0 < result['confidence'] <= 1

    def test_combine_failing_strategy(self):
        strategies = [('A', MockStrategy(1.0)), ('B', FailingStrategy())]
        sc = SignalCombiner(strategies)
        result = sc.combine({})
        # Should not crash; A's signal still comes through
        assert result['signal'] > 0

    def test_empty_strategies(self):
        with pytest.raises(ValueError):
            SignalCombiner([])

    def test_weight_mismatch(self):
        with pytest.raises(ValueError):
            SignalCombiner([('A', MockStrategy(1.0))], weights=[1, 2])

    def test_optimize_weights(self):
        strategies = [('A', MockStrategy(1.0, 0.9)), ('B', MockStrategy(-0.5, 0.3))]
        sc = SignalCombiner(strategies)
        data_series = [{}] * 20
        weights = sc.optimize_weights(data_series, metric='sharpe')
        assert len(weights) == 2
        assert abs(sum(weights) - 1.0) < 0.01

    def test_optimize_weights_returns(self):
        strategies = [('A', MockStrategy(1.0)), ('B', MockStrategy(0.5))]
        sc = SignalCombiner(strategies)
        weights = sc.optimize_weights([{}] * 10, metric='returns')
        assert len(weights) == 2

    def test_single_strategy(self):
        sc = SignalCombiner([('Solo', MockStrategy(0.7, 0.6))])
        result = sc.combine({})
        assert abs(result['signal'] - 0.7) < 0.001

    def test_signal_clamping(self):
        # Even with extreme signals, output should be [-1, 1]
        strategies = [('A', MockStrategy(1.0)), ('B', MockStrategy(1.0))]
        sc = SignalCombiner(strategies, weights=[5, 5])
        result = sc.combine({})
        assert -1 <= result['signal'] <= 1
