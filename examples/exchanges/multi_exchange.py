"""
FinClaw: Multi-Exchange Price Comparison
=========================================
Compare BTC prices across exchanges to spot arbitrage opportunities.

Usage:
    python multi_exchange.py
"""

from finclaw_ai import FinClaw
from finclaw_ai.exchanges import BinanceExchange, CoinbaseExchange, KrakenExchange

fc = FinClaw()

# Connect to multiple exchanges (public data, no API keys needed)
exchanges = {
    "Binance": BinanceExchange(),
    "Coinbase": CoinbaseExchange(),
    "Kraken": KrakenExchange(),
}

symbol = "BTC/USDT"
prices = {}

print(f"=== {symbol} Price Comparison ===\n")
for name, exchange in exchanges.items():
    ticker = exchange.get_ticker(symbol)
    prices[name] = ticker["price"]
    print(f"  {name:<12} ${ticker['price']:>12,.2f}  (vol: {ticker['volume']:,.0f})")

# Calculate arbitrage spread
max_ex = max(prices, key=prices.get)
min_ex = min(prices, key=prices.get)
spread = prices[max_ex] - prices[min_ex]
spread_pct = (spread / prices[min_ex]) * 100

print(f"\n  Spread: ${spread:,.2f} ({spread_pct:.3f}%)")
print(f"  Buy on {min_ex}, sell on {max_ex}")

if spread_pct > 0.1:
    print("  ⚡ Potential arbitrage opportunity!")
else:
    print("  ✅ Markets are well-aligned")
