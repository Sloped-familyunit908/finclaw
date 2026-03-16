"""
FinClaw Example: Custom Strategy
==================================
Build a custom strategy by combining indicators and plugging into the combiner.
"""

import numpy as np
from src.ta import rsi, macd, bollinger_bands
from src.strategies import StrategyCombiner, MomentumAdapter, MeanReversionAdapter

# --- Custom signal logic using raw indicators ---
np.random.seed(42)
prices = 100 * np.cumprod(1 + np.random.normal(0.0004, 0.018, 300))

rsi_vals = rsi(prices, period=14)
macd_line, macd_signal, macd_hist = macd(prices)
bb = bollinger_bands(prices, period=20)

# Simple composite: buy when RSI < 35 AND price below lower BB
buy_signals = (rsi_vals < 35) & (prices < bb["lower"])
print(f"Custom buy signals: {np.sum(~np.isnan(buy_signals) & buy_signals)} days")

# --- Or use the built-in combiner ---
combiner = StrategyCombiner()
combiner.add(MomentumAdapter(), weight=0.5)
combiner.add(MeanReversionAdapter(), weight=0.5)
signal = combiner.generate_signal(prices)
print(f"Combiner signal: {signal}")
