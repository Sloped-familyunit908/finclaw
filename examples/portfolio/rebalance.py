"""
FinClaw: Auto Portfolio Rebalancing
=====================================
Automatically rebalance your portfolio to target weights.

Usage:
    python rebalance.py
"""

from finclaw_ai import FinClaw
from finclaw_ai.portfolio import Rebalancer

fc = FinClaw()

# Define target allocation
target = {
    "AAPL": 0.20,   # 20% Apple
    "MSFT": 0.20,   # 20% Microsoft
    "GOOGL": 0.15,  # 15% Google
    "AMZN": 0.15,   # 15% Amazon
    "BND": 0.15,    # 15% Bonds ETF
    "GLD": 0.10,    # 10% Gold ETF
    "CASH": 0.05,   # 5% Cash
}

# Current holdings (from your broker or manual input)
current_holdings = {
    "AAPL": {"shares": 50, "value": 11_250},
    "MSFT": {"shares": 30, "value": 12_600},
    "GOOGL": {"shares": 20, "value": 3_520},
    "AMZN": {"shares": 15, "value": 2_835},
    "BND": {"shares": 100, "value": 7_200},
    "GLD": {"shares": 25, "value": 5_625},
    "CASH": {"shares": 1, "value": 6_970},
}

total_value = sum(h["value"] for h in current_holdings.values())

# Calculate rebalance trades
rebalancer = Rebalancer(target_weights=target, threshold=2.0)  # 2% drift threshold
trades = rebalancer.calculate(current_holdings, total_value)

print(f"=== Portfolio Rebalance (Total: ${total_value:,.0f}) ===\n")
print(f"{'Asset':<8} {'Current':>8} {'Target':>8} {'Drift':>8} {'Action':>12}")
print("-" * 48)

for t in trades:
    drift_str = f"{t['drift']:+.1f}%"
    if abs(t["drift"]) < rebalancer.threshold:
        action = "—"
    elif t["trade_value"] > 0:
        action = f"BUY ${t['trade_value']:,.0f}"
    else:
        action = f"SELL ${abs(t['trade_value']):,.0f}"
    print(f"{t['asset']:<8} {t['current_pct']:>7.1f}% {t['target_pct']:>7.1f}% {drift_str:>8} {action:>12}")

print(f"\nTrades needed: {sum(1 for t in trades if abs(t['drift']) >= rebalancer.threshold)}")
