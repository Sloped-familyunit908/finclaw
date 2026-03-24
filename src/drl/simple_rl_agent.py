"""
Simple Q-Learning Agent for finclaw evolution engine.

Pure numpy implementation — no stable-baselines3/pytorch/tensorflow dependencies.
Uses tabular Q-learning with discretized market states.

State space: (RSI bucket, price position bucket, volume state bucket)
Action space: SELL(-1), HOLD(0), BUY(1)
Reward: forward N-day returns

The agent outputs action probabilities via softmax over Q-values,
which are consumed by DRL factor files as evolution engine inputs.
"""

import json
import math
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# ============================================================
# Constants
# ============================================================

# Actions
ACTION_SELL = 0
ACTION_HOLD = 1
ACTION_BUY = 2
NUM_ACTIONS = 3
ACTION_LABELS = {ACTION_SELL: "SELL", ACTION_HOLD: "HOLD", ACTION_BUY: "BUY"}

# State discretization
RSI_BINS = [0, 20, 30, 40, 50, 60, 70, 80, 100]       # 8 bins
PRICE_POS_BINS = [0, 0.1, 0.25, 0.4, 0.5, 0.6, 0.75, 0.9, 1.0]  # 8 bins (percentile in N-day range)
VOLUME_BINS = [0, 0.5, 0.8, 1.0, 1.3, 2.0, 999]       # 6 bins (ratio to avg volume)

NUM_RSI_BINS = len(RSI_BINS) - 1       # 8
NUM_PRICE_BINS = len(PRICE_POS_BINS) - 1  # 8
NUM_VOL_BINS = len(VOLUME_BINS) - 1    # 6
NUM_STATES = NUM_RSI_BINS * NUM_PRICE_BINS * NUM_VOL_BINS  # 8*8*6 = 384

# Default Q-table path
DEFAULT_QTABLE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "drl", "q_table.json",
)


# ============================================================
# Helper: compute RSI from closes
# ============================================================

def _compute_rsi(closes: List[float], idx: int, period: int = 14) -> float:
    """Compute RSI at index `idx` using `period` bars. Returns 0-100."""
    if idx < period:
        return 50.0  # neutral default

    gains = 0.0
    losses = 0.0
    for i in range(idx - period + 1, idx + 1):
        delta = closes[i] - closes[i - 1]
        if delta > 0:
            gains += delta
        else:
            losses += abs(delta)

    avg_gain = gains / period
    avg_loss = losses / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def _compute_price_position(closes: List[float], highs: List[float],
                            lows: List[float], idx: int,
                            lookback: int = 20) -> float:
    """Where current price sits in its N-day high-low range. Returns 0-1."""
    start = max(0, idx - lookback + 1)
    if start >= idx:
        return 0.5

    period_high = max(highs[start: idx + 1])
    period_low = min(lows[start: idx + 1])
    rng = period_high - period_low
    if rng <= 0:
        return 0.5
    return (closes[idx] - period_low) / rng


def _compute_volume_ratio(volumes: List[float], idx: int,
                          lookback: int = 20) -> float:
    """Current volume / average volume over lookback. Returns ratio."""
    start = max(0, idx - lookback + 1)
    window = volumes[start: idx + 1]
    if len(window) < 2:
        return 1.0
    avg = sum(window[:-1]) / max(len(window) - 1, 1)
    if avg <= 0:
        return 1.0
    return volumes[idx] / avg


# ============================================================
# Discretize helpers
# ============================================================

def _digitize(value: float, bins: List[float]) -> int:
    """Return bin index for value given bin edges (like np.digitize but 0-indexed, clamped)."""
    for i in range(len(bins) - 1):
        if value < bins[i + 1]:
            return i
    return len(bins) - 2  # last bin


def encode_state(rsi: float, price_pos: float, vol_ratio: float) -> int:
    """Encode (RSI, price_position, volume_ratio) into a single state index."""
    r = _digitize(rsi, RSI_BINS)
    p = _digitize(price_pos, PRICE_POS_BINS)
    v = _digitize(vol_ratio, VOLUME_BINS)
    return r * (NUM_PRICE_BINS * NUM_VOL_BINS) + p * NUM_VOL_BINS + v


def compute_state_from_market(closes, highs, lows, volumes, idx) -> int:
    """Compute discretized state index from raw OHLCV at bar idx."""
    rsi = _compute_rsi(closes, idx)
    price_pos = _compute_price_position(closes, highs, lows, idx)
    vol_ratio = _compute_volume_ratio(volumes, idx)
    return encode_state(rsi, price_pos, vol_ratio)


# ============================================================
# Q-Learning Agent
# ============================================================

class QLearningAgent:
    """Tabular Q-Learning agent for market state → action mapping."""

    def __init__(
        self,
        num_states: int = NUM_STATES,
        num_actions: int = NUM_ACTIONS,
        learning_rate: float = 0.1,
        discount_factor: float = 0.95,
        epsilon: float = 0.2,
        epsilon_decay: float = 0.995,
        epsilon_min: float = 0.01,
    ):
        self.num_states = num_states
        self.num_actions = num_actions
        self.lr = learning_rate
        self.gamma = discount_factor
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min

        # Q-table: states × actions, initialized to 0
        self.q_table = np.zeros((num_states, num_actions), dtype=np.float64)
        self.visit_count = np.zeros((num_states, num_actions), dtype=np.int64)

    # ---- Core RL ----

    def choose_action(self, state: int) -> int:
        """Epsilon-greedy action selection."""
        if np.random.random() < self.epsilon:
            return np.random.randint(self.num_actions)
        return int(np.argmax(self.q_table[state]))

    def update(self, state: int, action: int, reward: float,
               next_state: int, done: bool = False):
        """Standard Q-learning update."""
        best_next = 0.0 if done else float(np.max(self.q_table[next_state]))
        td_target = reward + self.gamma * best_next
        td_error = td_target - self.q_table[state, action]
        self.q_table[state, action] += self.lr * td_error
        self.visit_count[state, action] += 1

    def decay_epsilon(self):
        """Decay exploration rate."""
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    # ---- Prediction interface ----

    def predict_action_probabilities(self, state: int, temperature: float = 1.0) -> np.ndarray:
        """Softmax over Q-values → action probabilities.
        
        Returns array of shape (3,): [P(SELL), P(HOLD), P(BUY)]
        """
        q_vals = self.q_table[state].copy()
        # Shift for numerical stability
        q_vals -= q_vals.max()
        exp_q = np.exp(q_vals / max(temperature, 1e-8))
        probs = exp_q / exp_q.sum()
        return probs

    def predict_buy_probability(self, state: int, temperature: float = 1.0) -> float:
        """Return probability of BUY action (0-1). Used as the DRL signal factor."""
        probs = self.predict_action_probabilities(state, temperature)
        return float(probs[ACTION_BUY])

    def state_value(self, state: int) -> float:
        """V(s) = max Q(s, a). Raw Q-value for best action in state."""
        return float(np.max(self.q_table[state]))

    # ---- Training ----

    def train_on_ohlcv(
        self,
        closes: List[float],
        highs: List[float],
        lows: List[float],
        volumes: List[float],
        forward_days: int = 5,
        episodes: int = 3,
    ) -> Dict[str, float]:
        """Train on a single OHLCV series.
        
        For each bar (with enough history), compute the state, pick an action,
        and use the forward N-day return as reward signal.
        
        Returns training stats dict.
        """
        n = len(closes)
        min_idx = 20  # need lookback for RSI/indicators
        max_idx = n - forward_days - 1  # need forward returns

        if max_idx <= min_idx:
            return {"episodes": 0, "updates": 0, "avg_reward": 0.0}

        total_reward = 0.0
        total_updates = 0

        for ep in range(episodes):
            for idx in range(min_idx, max_idx):
                state = compute_state_from_market(closes, highs, lows, volumes, idx)
                action = self.choose_action(state)

                # Reward: forward return
                future_price = closes[idx + forward_days]
                current_price = closes[idx]
                if current_price <= 0:
                    continue
                raw_return = (future_price - current_price) / current_price

                # Action-aligned reward:
                # BUY: reward = return (positive if price goes up)
                # SELL: reward = -return (positive if price goes down)
                # HOLD: reward = small penalty for indecision + tiny return
                if action == ACTION_BUY:
                    reward = raw_return * 10.0  # scale up for learning
                elif action == ACTION_SELL:
                    reward = -raw_return * 10.0
                else:  # HOLD
                    reward = -abs(raw_return) * 0.5  # small penalty

                next_idx = min(idx + 1, max_idx)
                next_state = compute_state_from_market(
                    closes, highs, lows, volumes, next_idx
                )
                done = (idx >= max_idx - 1)

                self.update(state, action, reward, next_state, done)
                total_reward += reward
                total_updates += 1

            self.decay_epsilon()

        avg_reward = total_reward / max(total_updates, 1)
        return {
            "episodes": episodes,
            "updates": total_updates,
            "avg_reward": round(avg_reward, 6),
            "epsilon": round(self.epsilon, 4),
        }

    # ---- Persistence ----

    def save(self, path: Optional[str] = None):
        """Save Q-table to JSON file."""
        path = path or DEFAULT_QTABLE_PATH
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {
            "num_states": self.num_states,
            "num_actions": self.num_actions,
            "q_table": self.q_table.tolist(),
            "visit_count": self.visit_count.tolist(),
            "epsilon": self.epsilon,
            "lr": self.lr,
            "gamma": self.gamma,
            "meta": {
                "rsi_bins": RSI_BINS,
                "price_pos_bins": PRICE_POS_BINS,
                "volume_bins": VOLUME_BINS,
            },
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: Optional[str] = None) -> "QLearningAgent":
        """Load Q-table from JSON file."""
        path = path or DEFAULT_QTABLE_PATH
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        agent = cls(
            num_states=data["num_states"],
            num_actions=data["num_actions"],
            learning_rate=data.get("lr", 0.1),
            discount_factor=data.get("gamma", 0.95),
            epsilon=data.get("epsilon", 0.01),
        )
        agent.q_table = np.array(data["q_table"], dtype=np.float64)
        agent.visit_count = np.array(data.get("visit_count",
            np.zeros_like(agent.q_table, dtype=np.int64)), dtype=np.int64)
        return agent


# ============================================================
# Cached loader (for factors to use)
# ============================================================

_cached_agent: Optional[QLearningAgent] = None
_cached_path: Optional[str] = None


def get_cached_agent(path: Optional[str] = None) -> Optional[QLearningAgent]:
    """Load and cache the Q-learning agent. Returns None if file doesn't exist."""
    global _cached_agent, _cached_path
    path = path or DEFAULT_QTABLE_PATH

    if _cached_agent is not None and _cached_path == path:
        return _cached_agent

    if not os.path.exists(path):
        return None

    try:
        _cached_agent = QLearningAgent.load(path)
        _cached_path = path
        return _cached_agent
    except Exception:
        return None


def clear_cache():
    """Clear the cached agent (useful for tests)."""
    global _cached_agent, _cached_path
    _cached_agent = None
    _cached_path = None
