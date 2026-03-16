"""
FinClaw Example: Backtest Momentum Strategy
============================================
Walk-forward backtest of the Jegadeesh-Titman momentum strategy on AAPL.
"""

import numpy as np
from src.strategies import MomentumJTStrategy
from src.backtesting import WalkForwardAnalyzer, MonteCarloSimulator

# --- Generate synthetic price data (replace with real data in production) ---
np.random.seed(42)
daily_returns = np.random.normal(0.0005, 0.02, 1260)  # ~5 years
prices = 100 * np.cumprod(1 + daily_returns)

# --- Strategy ---
strategy = MomentumJTStrategy()

# --- Walk-Forward Analysis ---
wfa = WalkForwardAnalyzer(n_splits=5, train_ratio=0.7)
wf_results = wfa.analyze(strategy, prices)
print("Walk-Forward Results:")
for key, val in wf_results.items():
    print(f"  {key}: {val}")

# --- Monte Carlo Simulation ---
mc = MonteCarloSimulator(n_simulations=1000, seed=42)
mc_results = mc.simulate(daily_returns)
print(f"\nMonte Carlo (1000 paths):")
print(f"  Median final value: {mc_results.get('median_final', 'N/A')}")
print(f"  5th percentile: {mc_results.get('percentile_5', 'N/A')}")
print(f"  95th percentile: {mc_results.get('percentile_95', 'N/A')}")
