"""
Factor: drl_q_learning_signal
Description: Q-learning agent buy probability — DRL signal for evolution engine
Category: drl
"""

import os
import sys

FACTOR_NAME = "drl_q_learning_signal"
FACTOR_DESC = "Q-learning agent buy probability — higher means DRL favors buying"
FACTOR_CATEGORY = "drl"

# Locate the project root so we can import src.drl
_FACTOR_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_FACTOR_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.drl.simple_rl_agent import (
    get_cached_agent,
    compute_state_from_market,
)


def compute(closes, highs, lows, volumes, idx):
    """Return DRL buy probability: 0 = strong sell, 0.5 = neutral, 1 = strong buy.
    
    Falls back to 0.5 if Q-table hasn't been trained yet.
    """
    # Need enough history for RSI / indicators
    if idx < 20:
        return 0.5

    agent = get_cached_agent()
    if agent is None:
        return 0.5

    try:
        state = compute_state_from_market(closes, highs, lows, volumes, idx)
        # Buy probability directly: 0-1
        buy_prob = agent.predict_buy_probability(state, temperature=1.0)

        # Map to signal: raw buy_prob is already 0-1
        # But we want more spread: use (buy_prob - sell_prob + 1) / 2
        probs = agent.predict_action_probabilities(state, temperature=1.0)
        sell_prob = float(probs[0])  # ACTION_SELL
        signal = (buy_prob - sell_prob + 1.0) / 2.0  # maps [-1,1] to [0,1]
        return max(0.0, min(1.0, signal))
    except Exception:
        return 0.5
