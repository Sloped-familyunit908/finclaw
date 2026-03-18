"""
Momentum / Trend Following Strategy
=====================================
Buy assets showing strong upward momentum; sell when momentum fades.

Uses multiple momentum signals:
- Rate of Change (ROC) over a lookback period
- Price relative to SMA (trend confirmation)
- Volume-weighted momentum for confirmation

Parameters:
    lookback: Momentum lookback period in bars (default: 20).
    sma_period: Trend-following SMA period (default: 50).
    roc_threshold: Minimum ROC to trigger entry (default: 0.05 = 5%).
    exit_roc_threshold: ROC below this triggers exit (default: -0.02 = -2%).
    volume_confirm: Require above-average volume (default: True).

Usage:
    strategy = MomentumStrategy(lookback=20, sma_period=50)
    signals = strategy.generate_signals(ohlcv_data)
"""

from __future__ import annotations
from typing import Any
from .base import Strategy, StrategySignal, StrategyMeta, sma as calc_sma, rsi as calc_rsi


class MomentumStrategy(Strategy):
    """Momentum-based trend following with volume confirmation."""

    def __init__(
        self,
        lookback: int = 20,
        sma_period: int = 50,
        roc_threshold: float = 0.05,
        exit_roc_threshold: float = -0.02,
        volume_confirm: bool = True,
        initial_capital: float = 10_000,
    ):
        super().__init__(initial_capital=initial_capital)
        if lookback < 2:
            raise ValueError("lookback must be >= 2")
        if sma_period < 2:
            raise ValueError("sma_period must be >= 2")
        self.lookback = lookback
        self.sma_period = sma_period
        self.roc_threshold = roc_threshold
        self.exit_roc_threshold = exit_roc_threshold
        self.volume_confirm = volume_confirm

    @classmethod
    def meta(cls) -> StrategyMeta:
        return StrategyMeta(
            name="Momentum",
            slug="momentum",
            category="universal",
            description="Buy on strong upward momentum (ROC + SMA trend filter). "
                        "Sell when momentum fades below exit threshold.",
            parameters={
                "lookback": "Momentum lookback period (default: 20)",
                "sma_period": "Trend SMA period (default: 50)",
                "roc_threshold": "Min ROC for entry (default: 0.05)",
                "exit_roc_threshold": "ROC exit threshold (default: -0.02)",
                "volume_confirm": "Require above-avg volume (default: True)",
            },
            usage_example="finclaw strategy backtest momentum --symbol AAPL --start 2024-01-01",
        )

    def generate_signals(self, data: list[dict[str, Any]]) -> list[StrategySignal]:
        signals: list[StrategySignal] = []
        closes = [bar["close"] for bar in data]
        volumes = [bar.get("volume", 0) for bar in data]
        min_bars = max(self.lookback, self.sma_period)

        for i in range(len(data)):
            price = data[i]["close"]

            if i < min_bars:
                signals.append(StrategySignal("hold", 0.0, price=price, reason="warming up"))
                continue

            # Rate of Change
            roc = (price / closes[i - self.lookback]) - 1.0

            # Short-term momentum (5-bar ROC)
            short_roc = (price / closes[i - min(5, self.lookback)]) - 1.0 if i >= 5 else 0

            # SMA trend filter
            sma_val = calc_sma(closes[: i + 1], self.sma_period)
            above_sma = sma_val is not None and price > sma_val

            # RSI momentum
            rsi_val = calc_rsi(closes[: i + 1], 14) if i >= 15 else None

            # Volume confirmation
            vol_ok = True
            if self.volume_confirm and volumes[i] > 0 and i >= 20:
                avg_vol = sum(volumes[i - 20: i]) / 20
                vol_ok = volumes[i] > avg_vol * 0.8  # slightly below avg is OK

            # Acceleration: momentum is increasing
            prev_roc = (closes[i - 1] / closes[i - 1 - self.lookback]) - 1.0 if i > self.lookback else 0
            accelerating = roc > prev_roc

            metadata = {
                "roc": roc,
                "short_roc": short_roc,
                "above_sma": above_sma,
                "rsi": rsi_val,
                "accelerating": accelerating,
            }

            # Buy: strong momentum + above SMA + volume confirms
            if roc >= self.roc_threshold and above_sma and vol_ok:
                confidence = min(0.5 + roc / 0.2, 1.0)  # higher ROC = higher confidence
                if accelerating:
                    confidence = min(confidence + 0.1, 1.0)
                if rsi_val is not None and 40 <= rsi_val <= 75:
                    confidence = min(confidence + 0.1, 1.0)
                signals.append(StrategySignal(
                    "buy", confidence, price=price,
                    reason=f"strong momentum ROC={roc:.2%} > {self.roc_threshold:.2%}, above SMA{self.sma_period}",
                    metadata=metadata,
                ))
            # Sell: momentum fades below exit threshold or breaks below SMA
            elif roc <= self.exit_roc_threshold or (not above_sma and roc < 0):
                confidence = min(0.5 + abs(roc) / 0.1, 1.0)
                reason_parts = []
                if roc <= self.exit_roc_threshold:
                    reason_parts.append(f"ROC={roc:.2%} < {self.exit_roc_threshold:.2%}")
                if not above_sma:
                    reason_parts.append(f"below SMA{self.sma_period}")
                signals.append(StrategySignal(
                    "sell", confidence, price=price,
                    reason="momentum fading: " + ", ".join(reason_parts),
                    metadata=metadata,
                ))
            else:
                signals.append(StrategySignal(
                    "hold", 0.0, price=price,
                    reason=f"ROC={roc:.2%}, {'above' if above_sma else 'below'} SMA{self.sma_period}",
                    metadata=metadata,
                ))

        return signals
