"""
FinClaw Example: Screen for Oversold Stocks
============================================
Use the stock screener to find RSI-oversold candidates.
"""

from src.screener import StockScreener

screener = StockScreener()

# Screen for oversold stocks: RSI < 30, above-average volume
results = screener.screen({
    "rsi_lt": 30,
    "volume_gt": 1.5,  # 1.5x average volume
})

print(f"Found {len(results)} oversold candidates:")
for stock in results:
    print(f"  {stock}")
