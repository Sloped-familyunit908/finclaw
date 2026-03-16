"""
RSI Divergence Strategy Plugin
Detects bullish/bearish RSI divergences for trade signals.
"""

from src.plugins.strategy_plugin import StrategyPlugin


class RSIDivergenceStrategy(StrategyPlugin):
    name = "rsi_divergence"
    version = "1.0.0"
    description = "RSI divergence detection strategy"

    def __init__(self):
        self.rsi_period = 14
        self.oversold = 30
        self.overbought = 70
        self.lookback = 5

    def _calculate_rsi(self, closes: list[float]) -> list[float]:
        """Calculate RSI values."""
        if len(closes) < self.rsi_period + 1:
            return []

        rsi_values = [None] * self.rsi_period
        gains = []
        losses = []

        for i in range(1, len(closes)):
            delta = closes[i] - closes[i - 1]
            gains.append(max(delta, 0))
            losses.append(max(-delta, 0))

        avg_gain = sum(gains[:self.rsi_period]) / self.rsi_period
        avg_loss = sum(losses[:self.rsi_period]) / self.rsi_period

        if avg_loss == 0:
            rsi_values.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100 - 100 / (1 + rs))

        for i in range(self.rsi_period, len(gains)):
            avg_gain = (avg_gain * (self.rsi_period - 1) + gains[i]) / self.rsi_period
            avg_loss = (avg_loss * (self.rsi_period - 1) + losses[i]) / self.rsi_period
            if avg_loss == 0:
                rsi_values.append(100.0)
            else:
                rs = avg_gain / avg_loss
                rsi_values.append(100 - 100 / (1 + rs))

        return rsi_values

    def generate_signals(self, data: dict) -> list:
        ohlcv = data.get("ohlcv", [])
        symbol = data.get("symbol", "UNKNOWN")
        signals = []

        if len(ohlcv) < self.rsi_period + self.lookback + 1:
            return signals

        closes = [c["close"] for c in ohlcv]
        rsi_values = self._calculate_rsi(closes)

        for i in range(self.rsi_period + self.lookback, len(closes)):
            rsi = rsi_values[i]
            if rsi is None:
                continue

            # Bullish divergence: price making lower low, RSI making higher low
            price_lower = closes[i] < min(closes[i - self.lookback:i])
            rsi_prev_min = min(r for r in rsi_values[i - self.lookback:i] if r is not None)
            rsi_higher = rsi > rsi_prev_min

            if price_lower and rsi_higher and rsi < self.oversold:
                signals.append({
                    "timestamp": ohlcv[i].get("timestamp"),
                    "action": "buy",
                    "symbol": symbol,
                    "confidence": (self.oversold - rsi) / self.oversold,
                    "reason": f"Bullish RSI divergence (RSI={rsi:.1f})",
                })

            # Bearish divergence: price making higher high, RSI making lower high
            price_higher = closes[i] > max(closes[i - self.lookback:i])
            rsi_prev_max = max(r for r in rsi_values[i - self.lookback:i] if r is not None)
            rsi_lower = rsi < rsi_prev_max

            if price_higher and rsi_lower and rsi > self.overbought:
                signals.append({
                    "timestamp": ohlcv[i].get("timestamp"),
                    "action": "sell",
                    "symbol": symbol,
                    "confidence": (rsi - self.overbought) / (100 - self.overbought),
                    "reason": f"Bearish RSI divergence (RSI={rsi:.1f})",
                })

        return signals

    def get_parameters(self) -> dict:
        return {
            "rsi_period": self.rsi_period,
            "oversold": self.oversold,
            "overbought": self.overbought,
            "lookback": self.lookback,
        }
