"""
Built-in Strategy Adapters
Wraps existing src/strategies/ classes as StrategyPlugin instances.
Maintains backward compatibility while exposing them through the plugin system.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.plugin_system.plugin_types import StrategyPlugin


class TrendFollowingPlugin(StrategyPlugin):
    """Wraps TrendFollowingStrategy as a plugin."""

    name = "trend_following"
    version = "1.0.0"
    description = "Dual MA crossover with ADX trend filter"
    author = "FinClaw"
    risk_level = "medium"
    markets = ["us_stock", "crypto", "forex", "cn_stock"]

    def __init__(self, fast_period: int = 20, slow_period: int = 50,
                 adx_period: int = 14, adx_threshold: float = 25.0):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        from src.strategies.trend_following import TrendFollowingStrategy
        strat = TrendFollowingStrategy(
            self.fast_period, self.slow_period, self.adx_period, self.adx_threshold
        )
        signals = pd.Series(0, index=data.index)
        prices = data["Close"].tolist()
        highs = data["High"].tolist() if "High" in data.columns else None
        lows = data["Low"].tolist() if "Low" in data.columns else None

        for i in range(self.slow_period + 2, len(prices)):
            sig = strat.generate_signal(prices[: i + 1], highs[:i+1] if highs else None, lows[:i+1] if lows else None)
            if sig.signal == "buy":
                signals.iloc[i] = 1
            elif sig.signal == "sell":
                signals.iloc[i] = -1
        return signals

    def get_parameters(self) -> dict[str, Any]:
        return {
            "fast_period": self.fast_period,
            "slow_period": self.slow_period,
            "adx_period": self.adx_period,
            "adx_threshold": self.adx_threshold,
        }


class MeanReversionPlugin(StrategyPlugin):
    """Wraps MeanReversionStrategy as a plugin."""

    name = "mean_reversion"
    version = "1.0.0"
    description = "RSI + Bollinger Bands mean reversion"
    author = "FinClaw"
    risk_level = "medium"
    markets = ["us_stock", "crypto", "cn_stock"]

    def __init__(self, rsi_period: int = 14, rsi_oversold: float = 30,
                 rsi_overbought: float = 70, bb_period: int = 20, bb_std: float = 2.0):
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.bb_period = bb_period
        self.bb_std = bb_std

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        from src.strategies.mean_reversion import MeanReversionStrategy
        strat = MeanReversionStrategy(
            self.rsi_period, self.rsi_oversold, self.rsi_overbought,
            self.bb_period, self.bb_std
        )
        signals = pd.Series(0, index=data.index)
        prices = data["Close"].tolist()
        min_len = max(self.rsi_period + 1, self.bb_period)

        for i in range(min_len, len(prices)):
            sig = strat.generate_signal(prices[: i + 1])
            if sig.signal == "buy":
                signals.iloc[i] = 1
            elif sig.signal == "sell":
                signals.iloc[i] = -1
        return signals

    def get_parameters(self) -> dict[str, Any]:
        return {
            "rsi_period": self.rsi_period,
            "rsi_oversold": self.rsi_oversold,
            "rsi_overbought": self.rsi_overbought,
            "bb_period": self.bb_period,
            "bb_std": self.bb_std,
        }


class MomentumPlugin(StrategyPlugin):
    """Wraps MomentumJTStrategy as a plugin."""

    name = "momentum_jt"
    version = "1.0.0"
    description = "Jegadeesh-Titman momentum strategy"
    author = "FinClaw"
    risk_level = "medium"
    markets = ["us_stock", "cn_stock"]

    def __init__(self, lookback: int = 252, hold_period: int = 21):
        self.lookback = lookback
        self.hold_period = hold_period

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        signals = pd.Series(0, index=data.index)
        prices = data["Close"]
        if len(prices) < self.lookback + 1:
            return signals
        momentum = prices / prices.shift(self.lookback) - 1
        signals[momentum > 0] = 1
        signals[momentum < 0] = -1
        return signals

    def get_parameters(self) -> dict[str, Any]:
        return {"lookback": self.lookback, "hold_period": self.hold_period}


class ValueMomentumPlugin(StrategyPlugin):
    """Wraps ValueMomentumStrategy as a plugin."""

    name = "value_momentum"
    version = "1.0.0"
    description = "Combined value and momentum factor strategy"
    author = "FinClaw"
    risk_level = "low"
    markets = ["us_stock", "cn_stock"]

    def __init__(self, momentum_period: int = 252, value_weight: float = 0.5):
        self.momentum_period = momentum_period
        self.value_weight = value_weight

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        signals = pd.Series(0, index=data.index)
        prices = data["Close"]
        if len(prices) < self.momentum_period + 1:
            return signals
        mom = prices / prices.shift(self.momentum_period) - 1
        signals[mom > 0.1] = 1
        signals[mom < -0.1] = -1
        return signals

    def get_parameters(self) -> dict[str, Any]:
        return {
            "momentum_period": self.momentum_period,
            "value_weight": self.value_weight,
        }


def get_builtin_plugins() -> list[StrategyPlugin]:
    """Return all built-in strategy plugins."""
    return [
        TrendFollowingPlugin(),
        MeanReversionPlugin(),
        MomentumPlugin(),
        ValueMomentumPlugin(),
    ]
