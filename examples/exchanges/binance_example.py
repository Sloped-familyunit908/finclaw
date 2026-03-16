"""
FinClaw: Binance Trading Example
=================================
Connect to Binance and execute trades.

Prerequisites:
    export BINANCE_API_KEY="your-api-key"
    export BINANCE_API_SECRET="your-api-secret"

Usage:
    python binance_example.py
"""

import os
from finclaw_ai import FinClaw
from finclaw_ai.exchanges import BinanceExchange

fc = FinClaw()

# Connect to Binance (uses env vars by default)
exchange = BinanceExchange(
    api_key=os.getenv("BINANCE_API_KEY"),
    api_secret=os.getenv("BINANCE_API_SECRET"),
    testnet=True,  # Use testnet for safety!
)

# Get account balance
balances = exchange.get_balances()
print("=== Balances ===")
for asset, amount in balances.items():
    if amount > 0:
        print(f"  {asset}: {amount}")

# Get BTC/USDT price
ticker = exchange.get_ticker("BTC/USDT")
print(f"\nBTC/USDT: ${ticker['price']:,.2f}")

# Place a limit buy order (testnet)
order = exchange.create_order(
    symbol="BTC/USDT",
    side="buy",
    order_type="limit",
    amount=0.001,
    price=ticker["price"] * 0.99,  # 1% below market
)
print(f"\nOrder placed: {order['id']} - {order['status']}")

# Check open orders
open_orders = exchange.get_open_orders("BTC/USDT")
print(f"Open orders: {len(open_orders)}")
