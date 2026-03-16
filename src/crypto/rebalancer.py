"""
Crypto Portfolio Rebalancer
Calculate rebalancing trades and backtest periodic rebalancing.
"""

from dataclasses import dataclass
import math


@dataclass
class RebalanceTrade:
    token: str
    action: str  # 'buy' or 'sell'
    amount_tokens: float
    amount_usd: float
    from_pct: float
    to_pct: float


class CryptoRebalancer:
    """Portfolio rebalancer with target allocation."""

    def __init__(self, target_allocation: dict[str, float]):
        """
        Args:
            target_allocation: e.g. {'BTC': 0.5, 'ETH': 0.3, 'SOL': 0.1, 'USDC': 0.1}
                Values must sum to 1.0 (with tolerance).
        """
        total = sum(target_allocation.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Target allocation must sum to 1.0, got {total}")
        if any(v < 0 for v in target_allocation.values()):
            raise ValueError("Allocations must be non-negative")
        self.target_allocation = target_allocation

    def calculate_trades(self, current_holdings: dict[str, float], prices: dict[str, float]) -> list[RebalanceTrade]:
        """Calculate trades needed to rebalance to target allocation.

        Args:
            current_holdings: {token: quantity} e.g. {'BTC': 0.5, 'ETH': 10}
            prices: {token: usd_price} e.g. {'BTC': 60000, 'ETH': 3000}

        Returns:
            List of RebalanceTrade.
        """
        # Calculate current portfolio value
        total_value = sum(
            current_holdings.get(token, 0) * prices.get(token, 0)
            for token in set(list(self.target_allocation.keys()) + list(current_holdings.keys()))
        )

        if total_value <= 0:
            return []

        trades = []
        for token, target_pct in self.target_allocation.items():
            current_qty = current_holdings.get(token, 0)
            price = prices.get(token, 0)
            if price <= 0:
                continue

            current_value = current_qty * price
            current_pct = current_value / total_value
            target_value = total_value * target_pct
            diff_value = target_value - current_value

            if abs(diff_value) < 1.0:  # ignore tiny differences
                continue

            diff_tokens = diff_value / price
            action = 'buy' if diff_value > 0 else 'sell'

            trades.append(RebalanceTrade(
                token=token,
                action=action,
                amount_tokens=round(abs(diff_tokens), 8),
                amount_usd=round(abs(diff_value), 2),
                from_pct=round(current_pct * 100, 2),
                to_pct=round(target_pct * 100, 2),
            ))

        trades.sort(key=lambda t: t.amount_usd, reverse=True)
        return trades

    def current_allocation(self, holdings: dict[str, float], prices: dict[str, float]) -> dict[str, float]:
        """Calculate current allocation percentages."""
        total = sum(holdings.get(t, 0) * prices.get(t, 0) for t in holdings)
        if total <= 0:
            return {}
        return {
            token: round(holdings.get(token, 0) * prices.get(token, 0) / total * 100, 2)
            for token in holdings
        }

    def drift(self, holdings: dict[str, float], prices: dict[str, float]) -> dict[str, float]:
        """Calculate drift from target for each token (in percentage points)."""
        alloc = self.current_allocation(holdings, prices)
        return {
            token: round(alloc.get(token, 0) - self.target_allocation.get(token, 0) * 100, 2)
            for token in set(list(alloc.keys()) + list(self.target_allocation.keys()))
        }

    def needs_rebalance(self, holdings: dict[str, float], prices: dict[str, float], threshold_pct: float = 5.0) -> bool:
        """Check if any token drifted beyond threshold."""
        d = self.drift(holdings, prices)
        return any(abs(v) > threshold_pct for v in d.values())

    def backtest_rebalancing(self, data: list[dict], period: str = 'monthly') -> dict:
        """Backtest periodic rebalancing.

        Args:
            data: list of dicts with 'prices' key: {token: price} per period.
            period: 'daily', 'weekly', 'monthly'.

        Returns:
            dict with start_value, end_value, return_pct, num_rebalances.
        """
        period_map = {'daily': 1, 'weekly': 7, 'monthly': 30}
        interval = period_map.get(period, 30)

        if not data:
            return {'start_value': 0, 'end_value': 0, 'return_pct': 0, 'num_rebalances': 0}

        # Start with $10000 allocated per target
        initial_value = 10000.0
        holdings = {}
        first_prices = data[0]['prices']
        for token, pct in self.target_allocation.items():
            price = first_prices.get(token, 1)
            holdings[token] = (initial_value * pct) / price if price > 0 else 0

        num_rebalances = 0
        for i, bar in enumerate(data):
            if i > 0 and i % interval == 0:
                prices = bar['prices']
                total = sum(holdings.get(t, 0) * prices.get(t, 0) for t in holdings)
                if total > 0:
                    for token, pct in self.target_allocation.items():
                        price = prices.get(token, 1)
                        holdings[token] = (total * pct) / price if price > 0 else 0
                    num_rebalances += 1

        final_prices = data[-1]['prices']
        end_value = sum(holdings.get(t, 0) * final_prices.get(t, 0) for t in holdings)
        return_pct = (end_value - initial_value) / initial_value * 100

        return {
            'start_value': initial_value,
            'end_value': round(end_value, 2),
            'return_pct': round(return_pct, 2),
            'num_rebalances': num_rebalances,
        }
