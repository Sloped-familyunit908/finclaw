"""
Crypto-Specific Trading Strategies
Grid trading, DCA, and cross-exchange arbitrage detection.
"""

from dataclasses import dataclass, field
from typing import Optional
import math


@dataclass
class GridSignal:
    action: str  # buy, sell, hold
    price: float
    grid_level: int
    reason: str


@dataclass
class DCASignal:
    action: str  # buy, hold
    amount: float
    period_index: int
    reason: str


@dataclass
class ArbitrageOpportunity:
    token: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    spread_pct: float
    estimated_profit: float


class GridBot:
    """Grid trading strategy for range-bound markets."""

    def __init__(self, lower: float, upper: float, grids: int = 10):
        if lower >= upper:
            raise ValueError("lower must be less than upper")
        if grids < 2:
            raise ValueError("grids must be at least 2")
        self.lower = lower
        self.upper = upper
        self.grids = grids
        self.grid_levels = self._calculate_grid_levels()
        self.filled_buys: set[int] = set()
        self.filled_sells: set[int] = set()

    def _calculate_grid_levels(self) -> list[float]:
        step = (self.upper - self.lower) / self.grids
        return [round(self.lower + i * step, 8) for i in range(self.grids + 1)]

    def generate_signals(self, data: list[dict]) -> list[GridSignal]:
        """Generate grid trading signals from price data.

        Args:
            data: list of dicts with at least 'close' key.

        Returns:
            List of GridSignal for each data point.
        """
        signals = []
        prev_price = None

        for i, bar in enumerate(data):
            price = bar['close']
            signal = GridSignal(action='hold', price=price, grid_level=-1, reason='no grid crossed')

            if prev_price is not None:
                for level_idx, level in enumerate(self.grid_levels):
                    # Price crossed down through a grid level → buy
                    if prev_price >= level > price and level_idx not in self.filled_buys:
                        signal = GridSignal(
                            action='buy',
                            price=level,
                            grid_level=level_idx,
                            reason=f'price crossed below grid {level_idx} at {level}',
                        )
                        self.filled_buys.add(level_idx)
                        self.filled_sells.discard(level_idx)
                        break
                    # Price crossed up through a grid level → sell
                    if prev_price <= level < price and level_idx not in self.filled_sells:
                        signal = GridSignal(
                            action='sell',
                            price=level,
                            grid_level=level_idx,
                            reason=f'price crossed above grid {level_idx} at {level}',
                        )
                        self.filled_sells.add(level_idx)
                        self.filled_buys.discard(level_idx)
                        break

            prev_price = price
            signals.append(signal)

        return signals

    def summary(self) -> dict:
        return {
            'lower': self.lower,
            'upper': self.upper,
            'grids': self.grids,
            'grid_spacing': round((self.upper - self.lower) / self.grids, 8),
            'levels': self.grid_levels,
        }


class DCAStrategy:
    """Dollar Cost Averaging for long-term accumulation."""

    VALID_PERIODS = ('daily', 'weekly', 'biweekly', 'monthly')

    def __init__(self, amount_per_period: float, period: str = 'weekly'):
        if amount_per_period <= 0:
            raise ValueError("amount_per_period must be positive")
        if period not in self.VALID_PERIODS:
            raise ValueError(f"period must be one of {self.VALID_PERIODS}")
        self.amount_per_period = amount_per_period
        self.period = period
        self._period_bars = self._get_period_bars()

    def _get_period_bars(self) -> int:
        mapping = {'daily': 1, 'weekly': 7, 'biweekly': 14, 'monthly': 30}
        return mapping[self.period]

    def generate_signals(self, data: list[dict]) -> list[DCASignal]:
        """Generate DCA buy signals at regular intervals.

        Args:
            data: list of dicts with 'close' key (one per day).

        Returns:
            List of DCASignal.
        """
        signals = []
        for i, bar in enumerate(data):
            if i % self._period_bars == 0:
                signals.append(DCASignal(
                    action='buy',
                    amount=self.amount_per_period,
                    period_index=i // self._period_bars,
                    reason=f'DCA buy #{i // self._period_bars} at {bar["close"]}',
                ))
            else:
                signals.append(DCASignal(
                    action='hold',
                    amount=0,
                    period_index=i // self._period_bars,
                    reason='waiting for next DCA period',
                ))
        return signals

    def backtest(self, data: list[dict]) -> dict:
        """Simple DCA backtest: total invested, total tokens, avg price."""
        total_invested = 0.0
        total_tokens = 0.0
        buys = 0
        for sig in self.generate_signals(data):
            if sig.action == 'buy':
                price = data[buys * self._period_bars]['close'] if buys * self._period_bars < len(data) else data[-1]['close']
                tokens = self.amount_per_period / price
                total_invested += self.amount_per_period
                total_tokens += tokens
                buys += 1
        avg_price = total_invested / total_tokens if total_tokens > 0 else 0
        final_price = data[-1]['close'] if data else 0
        return {
            'total_invested': round(total_invested, 2),
            'total_tokens': round(total_tokens, 8),
            'avg_price': round(avg_price, 2),
            'final_price': final_price,
            'pnl_pct': round((final_price - avg_price) / avg_price * 100, 2) if avg_price > 0 else 0,
            'num_buys': buys,
        }


class ArbitrageDetector:
    """Cross-exchange arbitrage detection."""

    def __init__(self, min_spread_pct: float = 0.5, fee_pct: float = 0.1):
        self.min_spread_pct = min_spread_pct
        self.fee_pct = fee_pct

    def detect(self, prices: dict[str, dict]) -> list[ArbitrageOpportunity]:
        """Detect arbitrage opportunities across exchanges.

        Args:
            prices: {token: {exchange: price}} e.g. {'BTC': {'binance': 60000, 'coinbase': 60500}}

        Returns:
            List of ArbitrageOpportunity sorted by spread descending.
        """
        opportunities = []

        for token, exchange_prices in prices.items():
            exchanges = list(exchange_prices.keys())
            for i in range(len(exchanges)):
                for j in range(len(exchanges)):
                    if i == j:
                        continue
                    buy_ex = exchanges[i]
                    sell_ex = exchanges[j]
                    buy_price = exchange_prices[buy_ex]
                    sell_price = exchange_prices[sell_ex]

                    if buy_price <= 0:
                        continue

                    spread_pct = (sell_price - buy_price) / buy_price * 100
                    net_spread = spread_pct - (self.fee_pct * 2)  # fees on both sides

                    if net_spread >= self.min_spread_pct:
                        opportunities.append(ArbitrageOpportunity(
                            token=token,
                            buy_exchange=buy_ex,
                            sell_exchange=sell_ex,
                            buy_price=buy_price,
                            sell_price=sell_price,
                            spread_pct=round(spread_pct, 4),
                            estimated_profit=round(net_spread, 4),
                        ))

        opportunities.sort(key=lambda x: x.spread_pct, reverse=True)
        return opportunities

    def best_opportunity(self, prices: dict[str, dict]) -> Optional[ArbitrageOpportunity]:
        opps = self.detect(prices)
        return opps[0] if opps else None
