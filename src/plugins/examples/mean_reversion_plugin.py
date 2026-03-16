"""
Mean Reversion Strategy Plugin
Buys when price drops below SMA - threshold, sells when above SMA + threshold.
"""

from src.plugins.strategy_plugin import StrategyPlugin


class MeanReversionStrategy(StrategyPlugin):
    name = "mean_reversion"
    version = "1.0.0"
    description = "Mean reversion strategy using SMA and deviation threshold"

    def __init__(self):
        self.window = 20
        self.threshold = 0.02
        self.exit_threshold = 0.005

    def generate_signals(self, data: dict) -> list:
        ohlcv = data.get("ohlcv", [])
        symbol = data.get("symbol", "UNKNOWN")
        signals = []

        if len(ohlcv) < self.window:
            return signals

        closes = [c["close"] for c in ohlcv]

        for i in range(self.window, len(closes)):
            sma = sum(closes[i - self.window:i]) / self.window
            price = closes[i]
            deviation = (price - sma) / sma

            if deviation < -self.threshold:
                signals.append({
                    "timestamp": ohlcv[i].get("timestamp"),
                    "action": "buy",
                    "symbol": symbol,
                    "confidence": min(abs(deviation) / self.threshold, 1.0),
                    "reason": f"Price {deviation:.2%} below SMA({self.window})",
                })
            elif deviation > self.threshold:
                signals.append({
                    "timestamp": ohlcv[i].get("timestamp"),
                    "action": "sell",
                    "symbol": symbol,
                    "confidence": min(abs(deviation) / self.threshold, 1.0),
                    "reason": f"Price {deviation:.2%} above SMA({self.window})",
                })

        return signals

    def get_parameters(self) -> dict:
        return {
            "window": self.window,
            "threshold": self.threshold,
            "exit_threshold": self.exit_threshold,
        }

    def optimize(self, data: dict, metric: str = "sharpe") -> dict:
        best_params = self.get_parameters()
        best_score = -float("inf")

        for window in [10, 15, 20, 30, 50]:
            for threshold in [0.01, 0.02, 0.03, 0.05]:
                self.window = window
                self.threshold = threshold
                signals = self.generate_signals(data)
                # Simple scoring: more signals with high confidence
                score = sum(s.get("confidence", 0) for s in signals)
                if score > best_score:
                    best_score = score
                    best_params = self.get_parameters()

        self.window = best_params["window"]
        self.threshold = best_params["threshold"]
        return best_params
