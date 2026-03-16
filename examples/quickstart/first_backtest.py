"""
FinClaw Quickstart: Run Your First Backtest
=============================================
Backtest a simple moving average crossover strategy.

Usage:
    python first_backtest.py
"""

from finclaw_ai import FinClaw

fc = FinClaw()

# Define a simple SMA crossover strategy
result = fc.backtest(
    symbol="AAPL",
    strategy="sma_crossover",
    params={"fast_period": 10, "slow_period": 30},
    start="2024-01-01",
    end="2024-12-31",
    initial_capital=10_000,
)

# Print results
print("=== Backtest Results ===")
print(f"Total Return:    {result['total_return']:+.2f}%")
print(f"Sharpe Ratio:    {result['sharpe_ratio']:.2f}")
print(f"Max Drawdown:    {result['max_drawdown']:.2f}%")
print(f"Win Rate:        {result['win_rate']:.1f}%")
print(f"Total Trades:    {result['total_trades']}")
