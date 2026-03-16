"""
FinClaw: Funding Rate Arbitrage
================================
Monitor perpetual futures funding rates across exchanges
and identify arbitrage opportunities.

Usage:
    python funding_arb.py
"""

from finclaw_ai import FinClaw
from finclaw_ai.defi import FundingMonitor

fc = FinClaw()

# Monitor funding rates across exchanges
monitor = FundingMonitor(
    symbols=["BTC/USDT", "ETH/USDT", "SOL/USDT"],
    exchanges=["binance", "bybit", "okx"],
    threshold_annualized=15.0,  # Alert when annualized rate > 15%
)

# Get current funding rates
rates = monitor.get_rates()

print("=== Funding Rates (Annualized) ===\n")
print(f"{'Symbol':<12} {'Binance':>10} {'Bybit':>10} {'OKX':>10} {'Spread':>10}")
print("-" * 56)

for symbol in rates:
    row = rates[symbol]
    spread = max(row.values()) - min(row.values())
    print(
        f"{symbol:<12}"
        f" {row.get('binance', 0):>9.2f}%"
        f" {row.get('bybit', 0):>9.2f}%"
        f" {row.get('okx', 0):>9.2f}%"
        f" {spread:>9.2f}%"
    )

# Find arbitrage opportunities
opps = monitor.find_opportunities(min_spread=5.0)
print(f"\n=== Arbitrage Opportunities ({len(opps)}) ===")
for opp in opps:
    print(f"\n  {opp['symbol']}:")
    print(f"    Long on  {opp['long_exchange']:<10} (rate: {opp['long_rate']:+.2f}%)")
    print(f"    Short on {opp['short_exchange']:<10} (rate: {opp['short_rate']:+.2f}%)")
    print(f"    Net yield: {opp['net_yield']:.2f}% annualized")
