"""
FinClaw: Alpaca Paper Trading (Free!)
=======================================
Paper trade US stocks with zero risk using Alpaca's free API.

Sign up at: https://alpaca.markets (free account)

Prerequisites:
    export ALPACA_API_KEY="your-paper-key"
    export ALPACA_API_SECRET="your-paper-secret"

Usage:
    python alpaca_paper.py
"""

import os
from finclaw_ai import FinClaw
from finclaw_ai.exchanges import AlpacaExchange

fc = FinClaw()

# Connect to Alpaca paper trading
exchange = AlpacaExchange(
    api_key=os.getenv("ALPACA_API_KEY"),
    api_secret=os.getenv("ALPACA_API_SECRET"),
    paper=True,  # Paper trading mode
)

# Check account
account = exchange.get_account()
print(f"Account: ${account['equity']:,.2f} equity, ${account['buying_power']:,.2f} buying power")

# Get a quote
quote = fc.quote("AAPL")
print(f"\nAAPL: ${quote['price']:.2f}")

# Buy 10 shares of AAPL
order = exchange.create_order(
    symbol="AAPL",
    side="buy",
    order_type="market",
    amount=10,
)
print(f"Bought 10 AAPL: {order['status']}")

# Check positions
positions = exchange.get_positions()
print(f"\n=== Positions ({len(positions)}) ===")
for pos in positions:
    pnl = pos["unrealized_pnl"]
    print(f"  {pos['symbol']}: {pos['qty']} shares, P&L: ${pnl:+,.2f}")
