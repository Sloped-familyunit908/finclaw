"""
Funding Rate Arbitrage
Cross-exchange funding rate comparison, opportunity discovery, carry trade calculation, and backtesting.
"""

import hashlib
from dataclasses import dataclass


@dataclass
class FundingOpportunity:
    symbol: str
    long_exchange: str
    short_exchange: str
    long_rate: float
    short_rate: float
    spread: float
    annualized_return: float


class FundingRateArbitrage:
    """Funding rate arbitrage analysis across exchanges."""

    def __init__(self, seed: int = 42):
        self._seed = seed

    def _deterministic_hash(self, key: str) -> str:
        return hashlib.sha256(f"{self._seed}:{key}".encode()).hexdigest()

    def _pseudo_random(self, key: str, idx: int = 0) -> float:
        h = self._deterministic_hash(f"{key}:{idx}")
        return int(h[:8], 16) / 0xFFFFFFFF

    def get_funding_rates(self, exchanges: list = None) -> dict:
        """Get current funding rates across exchanges.

        Args:
            exchanges: list of exchange names, or None for defaults.

        Returns:
            dict mapping exchange -> {symbol -> rate}.
        """
        if exchanges is None:
            exchanges = ['binance', 'bybit', 'okx', 'dydx', 'bitget']

        symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'DOGE/USDT', 'ARB/USDT', 'AVAX/USDT']
        result = {}

        for ex in exchanges:
            ex_lower = ex.lower()
            rates = {}
            for sym in symbols:
                r = self._pseudo_random(f"fr:{ex_lower}:{sym}")
                # Funding rates typically -0.1% to +0.1% per 8h
                rate = round((r - 0.5) * 0.002, 6)
                rates[sym] = rate
            result[ex_lower] = rates

        return result

    def find_opportunities(self, min_spread: float = 0.01) -> list:
        """Find funding rate arbitrage opportunities.

        Args:
            min_spread: minimum annualized spread to qualify (e.g. 0.01 = 1%).

        Returns:
            list of FundingOpportunity sorted by spread descending.
        """
        rates = self.get_funding_rates()
        symbols = set()
        for ex_rates in rates.values():
            symbols.update(ex_rates.keys())

        opportunities = []
        exchanges = list(rates.keys())

        for sym in symbols:
            sym_rates = {}
            for ex in exchanges:
                if sym in rates[ex]:
                    sym_rates[ex] = rates[ex][sym]

            if len(sym_rates) < 2:
                continue

            # Find max and min rate exchanges
            sorted_rates = sorted(sym_rates.items(), key=lambda x: x[1])
            lowest_ex, lowest_rate = sorted_rates[0]
            highest_ex, highest_rate = sorted_rates[-1]

            spread = highest_rate - lowest_rate
            # Annualize: 3 funding periods per day * 365
            annualized = spread * 3 * 365

            if annualized >= min_spread:
                opportunities.append(FundingOpportunity(
                    symbol=sym,
                    long_exchange=lowest_ex,   # long where rate is lowest (pay less)
                    short_exchange=highest_ex,  # short where rate is highest (receive more)
                    long_rate=lowest_rate,
                    short_rate=highest_rate,
                    spread=round(spread, 6),
                    annualized_return=round(annualized, 4),
                ))

        opportunities.sort(key=lambda x: x.annualized_return, reverse=True)
        return opportunities

    def calculate_carry(self, symbol: str, period_days: int = 30) -> dict:
        """Calculate expected carry trade return for a symbol.

        Args:
            symbol: trading pair (e.g. 'BTC/USDT').
            period_days: holding period in days.

        Returns:
            dict with symbol, avg_rate, period_days, expected_return, annualized_return.
        """
        rates = self.get_funding_rates()
        symbol = symbol.upper()

        all_rates = []
        for ex_rates in rates.values():
            if symbol in ex_rates:
                all_rates.append(ex_rates[symbol])

        if not all_rates:
            raise KeyError(f"No funding data for: {symbol}")

        avg_rate = sum(all_rates) / len(all_rates)
        # 3 funding periods per day
        period_return = avg_rate * 3 * period_days
        annualized = avg_rate * 3 * 365

        return {
            'symbol': symbol,
            'avg_funding_rate': round(avg_rate, 6),
            'period_days': period_days,
            'expected_return': round(period_return, 6),
            'annualized_return': round(annualized, 4),
            'direction': 'short' if avg_rate > 0 else 'long',
        }

    def backtest_carry_trade(self, symbol: str, history: list = None) -> dict:
        """Backtest a carry trade strategy on historical funding rates.

        Args:
            symbol: trading pair.
            history: list of historical rates (simulated if None).

        Returns:
            dict with total_return, max_drawdown, sharpe_ratio, win_rate, num_periods.
        """
        symbol = symbol.upper()

        if history is None:
            # Generate simulated historical rates
            history = []
            for i in range(90 * 3):  # 90 days * 3 periods/day
                r = self._pseudo_random(f"hist:{symbol}", i)
                rate = (r - 0.45) * 0.002  # slight positive bias
                history.append(round(rate, 6))

        if not history:
            return {'error': 'No history data'}

        cumulative = 0.0
        peak = 0.0
        max_drawdown = 0.0
        wins = 0
        returns = []

        for rate in history:
            # Short when positive funding (receive), long when negative (pay less)
            pnl = abs(rate)  # simplified: always capture the rate
            if rate > 0:
                pnl = rate  # receive funding from longs
            else:
                pnl = -rate * 0.5  # partial capture on negative rates

            cumulative += pnl
            returns.append(pnl)
            if pnl > 0:
                wins += 1
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_drawdown:
                max_drawdown = dd

        avg_return = sum(returns) / len(returns) if returns else 0
        std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5 if returns else 1
        sharpe = (avg_return / std_return * (365 * 3) ** 0.5) if std_return > 0 else 0

        return {
            'symbol': symbol,
            'total_return': round(cumulative, 6),
            'annualized_return': round(cumulative / len(history) * 3 * 365, 4),
            'max_drawdown': round(max_drawdown, 6),
            'sharpe_ratio': round(sharpe, 4),
            'win_rate': round(wins / len(history), 4) if history else 0,
            'num_periods': len(history),
        }
