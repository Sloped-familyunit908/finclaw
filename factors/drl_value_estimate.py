"""
Factor: drl_value_estimate
Description: Q-learning state value estimate — how good DRL thinks the current state is
Category: drl
"""

import os
import sys

FACTOR_NAME = "drl_value_estimate"
FACTOR_DESC = "Q-learning state value estimate — normalized V(s) from DRL agent"
FACTOR_CATEGORY = "drl"

# Locate the project root so we can import src.drl
_FACTOR_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_FACTOR_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.drl.simple_rl_agent import (
    get_cached_agent,
    compute_state_from_market,
    NUM_STATES,
)


def compute(closes, highs, lows, volumes, idx):
    """Return normalized state value: 0 = worst state, 0.5 = average, 1 = best state.
    
    Falls back to 0.5 if Q-table hasn't been trained yet.
    """
    if idx < 20:
        return 0.5

    agent = get_cached_agent()
    if agent is None:
        return 0.5

    try:
        state = compute_state_from_market(closes, highs, lows, volumes, idx)
        v = agent.state_value(state)

        # Normalize V(s) across all states to [0, 1]
        # Using the full Q-table's min/max values
        all_values = agent.q_table.max(axis=1)  # V(s) for all states
        v_min = float(all_values.min())
        v_max = float(all_values.max())

        if v_max - v_min < 1e-10:
            # Q-table is uniform (untrained or all zero) → neutral
            return 0.5

        normalized = (v - v_min) / (v_max - v_min)
        return max(0.0, min(1.0, normalized))
    except Exception:
        return 0.5
