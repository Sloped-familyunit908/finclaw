"""
FinClaw Example: Portfolio Optimization
========================================
Track positions and rebalance to target weights.
"""

from src.portfolio import PortfolioTracker, PortfolioRebalancer

# --- Build a portfolio ---
tracker = PortfolioTracker(initial_cash=100_000)
tracker.execute_trade("AAPL", shares=100, price=150.0)
tracker.execute_trade("MSFT", shares=80, price=300.0)
tracker.execute_trade("GOOGL", shares=50, price=140.0)

snapshot = tracker.snapshot()
print(f"Portfolio snapshot: {snapshot}")

# --- Rebalance to equal weight ---
rebalancer = PortfolioRebalancer(threshold=0.02)
actions = rebalancer.rebalance(
    current={"AAPL": 0.35, "MSFT": 0.45, "GOOGL": 0.20},
    target={"AAPL": 0.33, "MSFT": 0.34, "GOOGL": 0.33},
)
print(f"\nRebalance actions:")
for a in actions:
    print(f"  {a}")
