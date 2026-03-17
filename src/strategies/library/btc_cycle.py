"""
BTC Cycle Indicator Strategy
==============================
Combines Fear & Greed Index + MVRV ratio + Hashrate Ribbon
to identify BTC market cycle tops and bottoms.

Generates BUY when all 3 indicate extreme fear / undervaluation.
Generates SELL when all 3 indicate extreme greed / overvaluation.
"""

from __future__ import annotations

from typing import Any

from .base import Strategy, StrategySignal, StrategyMeta, sma


class BTCCycleIndicator(Strategy):
    """BTC cycle indicator combining on-chain metrics for macro signals.

    Parameters:
        fear_greed_buy: Fear & Greed threshold for buy (below = buy signal). Default: 25.
        fear_greed_sell: Fear & Greed threshold for sell (above = sell signal). Default: 75.
        mvrv_buy: MVRV ratio below which = undervalued. Default: 1.0.
        mvrv_sell: MVRV ratio above which = overvalued. Default: 3.0.
        hashrate_sma_short: Short SMA period for hashrate ribbon. Default: 30.
        hashrate_sma_long: Long SMA period for hashrate ribbon. Default: 60.

    Data format:
        Each bar dict must include:
        - close: float (price)
        - fear_greed: int (0-100, optional, defaults to 50)
        - mvrv: float (optional, defaults to 1.5)
        - hashrate: float (optional, defaults to 0)
    """

    def __init__(
        self,
        fear_greed_buy: float = 25,
        fear_greed_sell: float = 75,
        mvrv_buy: float = 1.0,
        mvrv_sell: float = 3.0,
        hashrate_sma_short: int = 30,
        hashrate_sma_long: int = 60,
        initial_capital: float = 10_000,
        **kwargs: Any,
    ):
        super().__init__(initial_capital=initial_capital, **kwargs)
        self.fear_greed_buy = fear_greed_buy
        self.fear_greed_sell = fear_greed_sell
        self.mvrv_buy = mvrv_buy
        self.mvrv_sell = mvrv_sell
        self.hashrate_sma_short = hashrate_sma_short
        self.hashrate_sma_long = hashrate_sma_long

    @classmethod
    def meta(cls) -> StrategyMeta:
        return StrategyMeta(
            name="BTC Cycle Indicator",
            slug="btc-cycle",
            category="crypto",
            description="Macro BTC cycle detector using Fear & Greed + MVRV + Hashrate Ribbon. "
                        "BUY at extreme fear/undervaluation, SELL at extreme greed/overvaluation.",
            parameters={
                "fear_greed_buy": "F&G threshold for buy signal (default: 25)",
                "fear_greed_sell": "F&G threshold for sell signal (default: 75)",
                "mvrv_buy": "MVRV below this = undervalued (default: 1.0)",
                "mvrv_sell": "MVRV above this = overvalued (default: 3.0)",
                "hashrate_sma_short": "Short hashrate SMA period (default: 30)",
                "hashrate_sma_long": "Long hashrate SMA period (default: 60)",
            },
            usage_example="finclaw strategy backtest btc-cycle --symbol BTCUSDT --start 2023-01-01",
        )

    def generate_signals(self, data: list[dict[str, Any]]) -> list[StrategySignal]:
        """Generate BUY/SELL/HOLD signals based on combined on-chain indicators.

        Args:
            data: List of bar dicts with close, fear_greed, mvrv, hashrate.

        Returns:
            List of StrategySignal, one per bar.
        """
        signals: list[StrategySignal] = []
        hashrates: list[float] = []

        for i, bar in enumerate(data):
            price = bar["close"]
            fg = bar.get("fear_greed", 50)
            mvrv = bar.get("mvrv", 1.5)
            hr = bar.get("hashrate", 0.0)
            hashrates.append(hr)

            # Hashrate ribbon: short SMA vs long SMA
            hr_sma_short = sma(hashrates, self.hashrate_sma_short)
            hr_sma_long = sma(hashrates, self.hashrate_sma_long)

            # Determine individual signals
            fg_buy = fg <= self.fear_greed_buy
            fg_sell = fg >= self.fear_greed_sell
            mvrv_buy = mvrv <= self.mvrv_buy
            mvrv_sell = mvrv >= self.mvrv_sell

            # Hashrate ribbon: bullish when short < long (miner capitulation)
            hr_buy = False
            hr_sell = False
            if hr_sma_short is not None and hr_sma_long is not None and hr_sma_long > 0:
                hr_buy = hr_sma_short < hr_sma_long  # miner capitulation = buy
                hr_sell = hr_sma_short > hr_sma_long * 1.1  # strong hashrate = potential top

            # Combined signals: all 3 must agree
            if fg_buy and mvrv_buy and hr_buy:
                signals.append(StrategySignal(
                    action="buy",
                    confidence=0.9,
                    price=price,
                    reason=f"Cycle bottom: F&G={fg}, MVRV={mvrv:.2f}, HR ribbon bearish",
                    metadata={"fear_greed": fg, "mvrv": mvrv, "hashrate_ribbon": "capitulation"},
                ))
            elif fg_sell and mvrv_sell and hr_sell:
                signals.append(StrategySignal(
                    action="sell",
                    confidence=0.9,
                    price=price,
                    reason=f"Cycle top: F&G={fg}, MVRV={mvrv:.2f}, HR ribbon bullish",
                    metadata={"fear_greed": fg, "mvrv": mvrv, "hashrate_ribbon": "expansion"},
                ))
            else:
                signals.append(StrategySignal(
                    action="hold",
                    confidence=0.5,
                    price=price,
                    reason="No cycle extreme detected",
                ))

        return signals
