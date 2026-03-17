"""Built-in technical indicators — zero external dependencies."""

from .builtin import (
    sma, ema, rsi, macd, bollinger_bands, atr, stochastic_oscillator,
    vwap, obv, ichimoku, fibonacci_retracement, supertrend,
)
from .signals import (
    detect_golden_cross, detect_death_cross, detect_rsi_divergence,
    detect_macd_crossover, detect_bollinger_squeeze,
)

__all__ = [
    "sma", "ema", "rsi", "macd", "bollinger_bands", "atr",
    "stochastic_oscillator", "vwap", "obv", "ichimoku",
    "fibonacci_retracement", "supertrend",
    "detect_golden_cross", "detect_death_cross", "detect_rsi_divergence",
    "detect_macd_crossover", "detect_bollinger_squeeze",
]
