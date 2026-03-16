"""
FinClaw: Pairs Trading Strategy
================================
Statistical arbitrage: trade the spread between two correlated assets.

Usage:
    python pairs_trading.py
"""

from finclaw_ai import FinClaw
from finclaw_ai.strategies import PairsTradingStrategy

fc = FinClaw()

# Define a correlated pair
strategy = PairsTradingStrategy(
    long_symbol="KO",       # Coca-Cola
    short_symbol="PEP",     # PepsiCo
    lookback_period=60,     # Days for z-score calculation
    entry_zscore=2.0,       # Enter when spread deviates 2 std devs
    exit_zscore=0.5,        # Exit when spread reverts to 0.5 std devs
    stop_zscore=3.5,        # Stop loss at 3.5 std devs
)

# Backtest
result = fc.backtest(
    strategy=strategy,
    start="2023-01-01",
    end="2024-12-31",
    initial_capital=50_000,
)

print("=== Pairs Trading: KO / PEP ===")
print(f"Correlation:     {result['correlation']:.3f}")
print(f"Cointegration:   {'Yes ✅' if result['cointegrated'] else 'No ❌'}")
print(f"Total Return:    {result['total_return']:+.2f}%")
print(f"Sharpe Ratio:    {result['sharpe_ratio']:.2f}")
print(f"Max Drawdown:    {result['max_drawdown']:.2f}%")
print(f"Total Trades:    {result['total_trades']}")
print(f"Win Rate:        {result['win_rate']:.1f}%")
print(f"Avg Hold Time:   {result['avg_hold_days']:.1f} days")
