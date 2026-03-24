"""
Tests for DRL Q-learning signal factors.

Tests:
  1. Q-learning agent can train and predict
  2. Factors load correctly in FactorRegistry
  3. Return values are in [0, 1] range
  4. Graceful fallback to 0.5 when Q-table doesn't exist
"""

import json
import math
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.drl.simple_rl_agent import (
    QLearningAgent,
    compute_state_from_market,
    encode_state,
    get_cached_agent,
    clear_cache,
    NUM_STATES,
    NUM_ACTIONS,
    ACTION_BUY,
    ACTION_HOLD,
    ACTION_SELL,
    _compute_rsi,
    _compute_price_position,
    _compute_volume_ratio,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def sample_ohlcv():
    """Generate synthetic OHLCV data (100 bars of a trending market)."""
    np.random.seed(42)
    n = 100
    base = 100.0
    # Random walk with slight upward drift
    returns = np.random.normal(0.001, 0.02, n)
    closes = [base]
    for r in returns[1:]:
        closes.append(closes[-1] * (1 + r))

    highs = [c * (1 + abs(np.random.normal(0, 0.01))) for c in closes]
    lows = [c * (1 - abs(np.random.normal(0, 0.01))) for c in closes]
    volumes = [1000000 * (1 + np.random.normal(0, 0.3)) for _ in closes]
    volumes = [max(v, 100000) for v in volumes]

    return closes, highs, lows, volumes


@pytest.fixture
def trained_agent(sample_ohlcv, tmp_path):
    """Train a Q-learning agent on sample data and save to temp path."""
    closes, highs, lows, volumes = sample_ohlcv
    agent = QLearningAgent(epsilon=0.5)
    stats = agent.train_on_ohlcv(closes, highs, lows, volumes,
                                  forward_days=5, episodes=5)
    qtable_path = str(tmp_path / "q_table.json")
    agent.save(qtable_path)
    return agent, qtable_path, stats


# ============================================================
# Test: Q-learning agent basics
# ============================================================

class TestQLearningAgent:
    """Test the core Q-learning agent."""

    def test_init(self):
        agent = QLearningAgent()
        assert agent.q_table.shape == (NUM_STATES, NUM_ACTIONS)
        assert agent.visit_count.shape == (NUM_STATES, NUM_ACTIONS)
        assert agent.epsilon > 0

    def test_choose_action_returns_valid(self):
        agent = QLearningAgent()
        for _ in range(50):
            action = agent.choose_action(0)
            assert action in (ACTION_SELL, ACTION_HOLD, ACTION_BUY)

    def test_update_changes_qtable(self):
        agent = QLearningAgent(epsilon=0.0)
        old_val = agent.q_table[0, ACTION_BUY]
        agent.update(0, ACTION_BUY, 1.0, 1, done=False)
        new_val = agent.q_table[0, ACTION_BUY]
        assert new_val != old_val
        assert new_val > old_val  # positive reward should increase Q

    def test_train_on_ohlcv(self, sample_ohlcv):
        closes, highs, lows, volumes = sample_ohlcv
        agent = QLearningAgent(epsilon=0.5)
        stats = agent.train_on_ohlcv(closes, highs, lows, volumes,
                                      forward_days=5, episodes=2)
        assert stats["episodes"] == 2
        assert stats["updates"] > 0
        # Q-table should no longer be all zeros
        assert np.any(agent.q_table != 0)

    def test_predict_action_probabilities_sum_to_one(self):
        agent = QLearningAgent()
        agent.q_table[10] = [1.0, 2.0, 0.5]
        probs = agent.predict_action_probabilities(10)
        assert abs(probs.sum() - 1.0) < 1e-6
        assert all(p >= 0 for p in probs)

    def test_predict_buy_probability_range(self, trained_agent):
        agent, _, _ = trained_agent
        for state_idx in range(0, NUM_STATES, 50):
            p = agent.predict_buy_probability(state_idx)
            assert 0.0 <= p <= 1.0

    def test_state_value(self):
        agent = QLearningAgent()
        agent.q_table[5] = [-1.0, 0.5, 2.0]
        assert agent.state_value(5) == 2.0

    def test_decay_epsilon(self):
        agent = QLearningAgent(epsilon=1.0, epsilon_decay=0.5, epsilon_min=0.01)
        agent.decay_epsilon()
        assert agent.epsilon == 0.5
        agent.decay_epsilon()
        assert agent.epsilon == 0.25


# ============================================================
# Test: Persistence (save/load)
# ============================================================

class TestPersistence:
    """Test Q-table save and load."""

    def test_save_and_load(self, trained_agent):
        agent, path, _ = trained_agent
        # Load back
        loaded = QLearningAgent.load(path)
        assert loaded.q_table.shape == agent.q_table.shape
        np.testing.assert_array_almost_equal(loaded.q_table, agent.q_table)

    def test_save_creates_directory(self, tmp_path):
        agent = QLearningAgent()
        nested = str(tmp_path / "deep" / "nested" / "q_table.json")
        agent.save(nested)
        assert os.path.exists(nested)

    def test_load_file(self, tmp_path):
        """Verify the JSON structure."""
        agent = QLearningAgent()
        agent.q_table[0, 0] = 42.0
        path = str(tmp_path / "q_table.json")
        agent.save(path)

        with open(path, "r") as f:
            data = json.load(f)
        assert data["num_states"] == NUM_STATES
        assert data["num_actions"] == NUM_ACTIONS
        assert data["q_table"][0][0] == 42.0
        assert "meta" in data


# ============================================================
# Test: State encoding
# ============================================================

class TestStateEncoding:
    """Test market state discretization."""

    def test_encode_state_range(self):
        """All encoded states should be in [0, NUM_STATES)."""
        for rsi in [0, 15, 25, 35, 45, 55, 65, 75, 95]:
            for pp in [0.05, 0.15, 0.3, 0.45, 0.55, 0.65, 0.8, 0.95]:
                for vr in [0.3, 0.6, 0.9, 1.1, 1.5, 3.0]:
                    s = encode_state(rsi, pp, vr)
                    assert 0 <= s < NUM_STATES, f"state {s} out of range for rsi={rsi}, pp={pp}, vr={vr}"

    def test_compute_rsi_basic(self):
        # Create a series where price goes up every day
        closes = [100 + i for i in range(30)]
        rsi = _compute_rsi(closes, 29)
        assert rsi == 100.0  # all gains, no losses

    def test_compute_rsi_neutral(self):
        """RSI should be ~50 for balanced up/down."""
        closes = [100.0]
        for i in range(1, 30):
            if i % 2 == 0:
                closes.append(closes[-1] + 1.0)
            else:
                closes.append(closes[-1] - 1.0)
        rsi = _compute_rsi(closes, 29)
        assert 40.0 <= rsi <= 60.0

    def test_compute_price_position(self):
        closes = list(range(80, 101))  # 80..100
        highs = [c + 1 for c in closes]
        lows = [c - 1 for c in closes]
        pos = _compute_price_position(closes, highs, lows, len(closes) - 1)
        # Current price 100, range roughly 79-101 → near top
        assert pos > 0.8

    def test_compute_state_from_market(self, sample_ohlcv):
        closes, highs, lows, volumes = sample_ohlcv
        for idx in range(20, len(closes)):
            state = compute_state_from_market(closes, highs, lows, volumes, idx)
            assert 0 <= state < NUM_STATES


# ============================================================
# Test: Factor files
# ============================================================

class TestDRLFactors:
    """Test the factor compute() functions."""

    def test_signal_factor_no_qtable(self, sample_ohlcv):
        """Without a Q-table, drl_q_learning_signal should return 0.5."""
        clear_cache()
        # Make sure there's no default Q-table
        import factors.drl_q_learning_signal as sig_mod
        # Force a reload to clear any cached agent
        clear_cache()

        closes, highs, lows, volumes = sample_ohlcv
        val = sig_mod.compute(closes, highs, lows, volumes, 50)
        assert val == 0.5

    def test_value_factor_no_qtable(self, sample_ohlcv):
        """Without a Q-table, drl_value_estimate should return 0.5."""
        clear_cache()
        import factors.drl_value_estimate as val_mod

        closes, highs, lows, volumes = sample_ohlcv
        val = val_mod.compute(closes, highs, lows, volumes, 50)
        assert val == 0.5

    def test_signal_factor_with_qtable(self, sample_ohlcv, trained_agent):
        """With a trained Q-table, factor should return value in [0, 1]."""
        agent, path, _ = trained_agent
        clear_cache()

        import src.drl.simple_rl_agent as rl_mod
        original_default = rl_mod.DEFAULT_QTABLE_PATH
        try:
            rl_mod.DEFAULT_QTABLE_PATH = path
            clear_cache()

            import factors.drl_q_learning_signal as sig_mod
            closes, highs, lows, volumes = sample_ohlcv

            for idx in range(20, len(closes)):
                val = sig_mod.compute(closes, highs, lows, volumes, idx)
                assert 0.0 <= val <= 1.0, f"Signal factor returned {val} at idx={idx}"
        finally:
            rl_mod.DEFAULT_QTABLE_PATH = original_default
            clear_cache()

    def test_value_factor_with_qtable(self, sample_ohlcv, trained_agent):
        """With a trained Q-table, value estimate should return value in [0, 1]."""
        agent, path, _ = trained_agent
        clear_cache()

        import src.drl.simple_rl_agent as rl_mod
        original_default = rl_mod.DEFAULT_QTABLE_PATH
        try:
            rl_mod.DEFAULT_QTABLE_PATH = path
            clear_cache()

            import factors.drl_value_estimate as val_mod
            closes, highs, lows, volumes = sample_ohlcv

            for idx in range(20, len(closes)):
                val = val_mod.compute(closes, highs, lows, volumes, idx)
                assert 0.0 <= val <= 1.0, f"Value factor returned {val} at idx={idx}"
        finally:
            rl_mod.DEFAULT_QTABLE_PATH = original_default
            clear_cache()

    def test_signal_factor_early_index(self, sample_ohlcv):
        """Factor should return 0.5 for early indices (not enough history)."""
        import factors.drl_q_learning_signal as sig_mod
        closes, highs, lows, volumes = sample_ohlcv
        val = sig_mod.compute(closes, highs, lows, volumes, 5)
        assert val == 0.5

    def test_value_factor_early_index(self, sample_ohlcv):
        """Factor should return 0.5 for early indices."""
        import factors.drl_value_estimate as val_mod
        closes, highs, lows, volumes = sample_ohlcv
        val = val_mod.compute(closes, highs, lows, volumes, 5)
        assert val == 0.5


# ============================================================
# Test: FactorRegistry integration
# ============================================================

class TestFactorRegistryIntegration:
    """Test that DRL factors load correctly into FactorRegistry."""

    def test_factors_loadable_by_registry(self):
        """FactorRegistry should discover and load drl_* factors."""
        from src.evolution.factor_discovery import FactorRegistry

        factors_dir = os.path.join(PROJECT_ROOT, "factors")
        registry = FactorRegistry(factors_dir)
        count = registry.load_all()

        assert count > 0, "No factors loaded"
        assert "drl_q_learning_signal" in registry.factors, \
            f"drl_q_learning_signal not found. Keys: {list(registry.factors.keys())[:10]}"
        assert "drl_value_estimate" in registry.factors, \
            f"drl_value_estimate not found."

    def test_registry_factor_metadata(self):
        """Check factor metadata is correct."""
        from src.evolution.factor_discovery import FactorRegistry

        factors_dir = os.path.join(PROJECT_ROOT, "factors")
        registry = FactorRegistry(factors_dir)
        registry.load_all()

        sig = registry.factors.get("drl_q_learning_signal")
        assert sig is not None
        assert sig.category == "drl"
        assert "Q-learning" in sig.description or "buy probability" in sig.description

        val = registry.factors.get("drl_value_estimate")
        assert val is not None
        assert val.category == "drl"

    def test_registry_factor_compute(self, sample_ohlcv):
        """Factors loaded via registry should produce valid outputs."""
        clear_cache()
        from src.evolution.factor_discovery import FactorRegistry

        factors_dir = os.path.join(PROJECT_ROOT, "factors")
        registry = FactorRegistry(factors_dir)
        registry.load_all()

        closes, highs, lows, volumes = sample_ohlcv

        for name in ("drl_q_learning_signal", "drl_value_estimate"):
            factor = registry.factors[name]
            val = factor.compute_fn(closes, highs, lows, volumes, 50)
            assert 0.0 <= val <= 1.0, f"{name} returned {val}"
