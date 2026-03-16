"""
FinClaw Quickstart: Screen Stocks
==================================
Find stocks matching your criteria.

Usage:
    python first_screen.py
"""

from finclaw_ai import FinClaw

fc = FinClaw()

# Screen for undervalued large-caps with momentum
results = fc.screen(
    market_cap_min=10_000_000_000,   # $10B+
    pe_ratio_max=20,                  # P/E under 20
    rsi_max=50,                       # Not overbought
    volume_min=1_000_000,             # Liquid stocks
    sort_by="market_cap",
    limit=10,
)

print("=== Stock Screener Results ===")
print(f"{'Symbol':<8} {'Price':>10} {'P/E':>8} {'RSI':>6} {'Market Cap':>14}")
print("-" * 50)
for stock in results:
    mcap = f"${stock['market_cap'] / 1e9:.1f}B"
    print(f"{stock['symbol']:<8} ${stock['price']:>8.2f} {stock['pe_ratio']:>8.1f} {stock['rsi']:>6.1f} {mcap:>14}")
