"""
FinClaw: Portfolio Optimization
================================
Find the optimal asset allocation using Modern Portfolio Theory.

Usage:
    python optimize.py
"""

from finclaw_ai import FinClaw
from finclaw_ai.portfolio import PortfolioOptimizer

fc = FinClaw()

# Define your universe
assets = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "BRK-B", "JPM", "V", "UNH", "XOM"]

# Optimize portfolio
optimizer = PortfolioOptimizer(
    assets=assets,
    start="2022-01-01",
    end="2024-12-31",
    risk_free_rate=0.05,  # 5% risk-free rate
)

# Max Sharpe ratio portfolio
max_sharpe = optimizer.optimize(objective="max_sharpe")

print("=== Max Sharpe Portfolio ===")
print(f"Expected Return: {max_sharpe['expected_return']:.2f}%")
print(f"Volatility:      {max_sharpe['volatility']:.2f}%")
print(f"Sharpe Ratio:    {max_sharpe['sharpe_ratio']:.2f}")
print(f"\nAllocation:")
for asset, weight in sorted(max_sharpe["weights"].items(), key=lambda x: -x[1]):
    if weight > 0.01:
        bar = "█" * int(weight * 50)
        print(f"  {asset:<6} {weight:>6.1%}  {bar}")

# Minimum volatility portfolio
min_vol = optimizer.optimize(objective="min_volatility")
print(f"\n=== Min Volatility Portfolio ===")
print(f"Expected Return: {min_vol['expected_return']:.2f}%")
print(f"Volatility:      {min_vol['volatility']:.2f}%")
print(f"Sharpe Ratio:    {min_vol['sharpe_ratio']:.2f}")
