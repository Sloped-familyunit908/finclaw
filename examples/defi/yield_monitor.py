"""
FinClaw: DeFi Yield Monitoring
================================
Track and compare yields across DeFi protocols.

Usage:
    python yield_monitor.py
"""

from finclaw_ai import FinClaw
from finclaw_ai.defi import YieldMonitor

fc = FinClaw()

# Monitor yields across protocols
monitor = YieldMonitor(
    protocols=["aave", "compound", "curve", "lido", "maker"],
    assets=["USDC", "USDT", "ETH", "WBTC"],
    chains=["ethereum", "arbitrum", "polygon"],
)

# Get current yields
yields = monitor.get_yields()

print("=== DeFi Yield Monitor ===\n")
print(f"{'Protocol':<12} {'Asset':<8} {'Chain':<12} {'APY':>8} {'TVL':>14} {'Risk':>6}")
print("-" * 64)

for y in sorted(yields, key=lambda x: x["apy"], reverse=True)[:15]:
    tvl = f"${y['tvl'] / 1e6:.1f}M" if y["tvl"] > 1e6 else f"${y['tvl'] / 1e3:.0f}K"
    risk = {"low": "🟢", "medium": "🟡", "high": "🔴"}[y["risk_level"]]
    print(
        f"{y['protocol']:<12} {y['asset']:<8} {y['chain']:<12}"
        f" {y['apy']:>7.2f}% {tvl:>14} {risk:>6}"
    )

# Best risk-adjusted yields
print(f"\n=== Top Risk-Adjusted Yields ===")
best = monitor.get_best_yields(risk_max="medium", min_tvl=1_000_000)
for i, y in enumerate(best[:5], 1):
    print(f"  {i}. {y['protocol']}/{y['asset']} on {y['chain']}: {y['apy']:.2f}% APY")
