"""
FinClaw: Grid Trading Bot
===========================
A grid bot places buy/sell orders at fixed intervals around the current price.
Profits from range-bound markets.

Usage:
    python grid_bot.py
"""

from finclaw_ai import FinClaw
from finclaw_ai.strategies import GridStrategy

fc = FinClaw()

# Configure grid strategy
strategy = GridStrategy(
    symbol="ETH/USDT",
    lower_price=2000,       # Grid lower bound
    upper_price=3000,       # Grid upper bound
    num_grids=20,           # Number of grid levels
    total_investment=5000,  # Total capital to deploy
)

# Backtest the grid strategy
result = fc.backtest(
    strategy=strategy,
    start="2024-06-01",
    end="2024-12-31",
)

print("=== Grid Bot Backtest ===")
print(f"Grid Range:      ${strategy.lower_price:,} - ${strategy.upper_price:,}")
print(f"Grid Levels:     {strategy.num_grids}")
print(f"Investment:      ${strategy.total_investment:,}")
print(f"")
print(f"Total Return:    {result['total_return']:+.2f}%")
print(f"Grid Profit:     ${result['grid_profit']:,.2f}")
print(f"Total Trades:    {result['total_trades']}")
print(f"Avg Trade P&L:   ${result['avg_trade_pnl']:,.2f}")

# Show grid levels
print(f"\n=== Grid Levels ===")
for level in strategy.get_grid_levels()[:5]:
    print(f"  ${level['price']:>10,.2f}  {level['side']:<5}  {level['amount']:.4f} ETH")
print(f"  ... ({strategy.num_grids - 5} more levels)")
