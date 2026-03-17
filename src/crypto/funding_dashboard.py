"""
Multi-Exchange Funding Rate Dashboard
======================================
Aggregate funding rates from Binance, Bybit, OKX for perpetual swaps.
Identify arbitrage opportunities and provide historical analysis.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from src.exchanges.http_client import HttpClient, ExchangeAPIError, ExchangeConnectionError


@dataclass
class FundingRate:
    """Funding rate data for a single symbol on one exchange."""
    exchange: str
    symbol: str
    rate: float  # 8h rate as decimal, e.g., 0.0001 = 0.01%
    annualized: float  # annualized rate %
    next_funding_time: int = 0  # unix timestamp
    timestamp: int = field(default_factory=lambda: int(time.time()))


@dataclass
class FundingArbitrage:
    """Arbitrage opportunity between two exchanges."""
    symbol: str
    long_exchange: str  # exchange with lower funding (pay less)
    short_exchange: str  # exchange with higher funding (receive more)
    spread: float  # annualized spread %
    long_rate: float
    short_rate: float


@dataclass
class FundingDashboard:
    """Aggregated funding rate dashboard data."""
    rates: list[FundingRate]
    arbitrage_opportunities: list[FundingArbitrage]
    timestamp: int = field(default_factory=lambda: int(time.time()))


SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]


def _annualize_8h_rate(rate: float) -> float:
    """Convert 8h funding rate to annualized percentage."""
    return round(rate * 3 * 365 * 100, 4)


class FundingDashboardClient:
    """Aggregates funding rates from multiple exchanges.

    Fetches from Binance, Bybit, OKX public APIs (no key required).
    Falls back to simulated data when APIs are unreachable.
    """

    def __init__(self, timeout: int = 10):
        self._binance = HttpClient("https://fapi.binance.com", timeout=timeout)
        self._bybit = HttpClient("https://api.bybit.com", timeout=timeout)
        self._okx = HttpClient("https://www.okx.com", timeout=timeout)
        self._timeout = timeout

    def get_all_rates(self, symbols: list[str] | None = None) -> list[FundingRate]:
        """Fetch current funding rates from all exchanges.

        Args:
            symbols: List of symbols (default: BTCUSDT, ETHUSDT, SOLUSDT).

        Returns:
            List of FundingRate across all exchanges.
        """
        symbols = symbols or SYMBOLS
        rates: list[FundingRate] = []
        rates.extend(self._fetch_binance(symbols))
        rates.extend(self._fetch_bybit(symbols))
        rates.extend(self._fetch_okx(symbols))
        return rates

    def get_dashboard(self, symbols: list[str] | None = None, min_spread: float = 5.0) -> FundingDashboard:
        """Get full dashboard with rates and arbitrage opportunities.

        Args:
            symbols: Symbols to track.
            min_spread: Minimum annualized spread (%) to flag as arbitrage.

        Returns:
            FundingDashboard with rates and opportunities.
        """
        rates = self.get_all_rates(symbols)
        arbs = self.find_arbitrage(rates, min_spread)
        return FundingDashboard(rates=rates, arbitrage_opportunities=arbs)

    def find_arbitrage(self, rates: list[FundingRate], min_spread: float = 5.0) -> list[FundingArbitrage]:
        """Identify funding rate arbitrage opportunities.

        Long on the exchange with lower rate, short on exchange with higher rate.

        Args:
            rates: List of funding rates to analyze.
            min_spread: Minimum annualized spread (%) to qualify.

        Returns:
            List of FundingArbitrage opportunities.
        """
        # Group by symbol
        by_symbol: dict[str, list[FundingRate]] = {}
        for r in rates:
            by_symbol.setdefault(r.symbol, []).append(r)

        opportunities: list[FundingArbitrage] = []
        for symbol, sym_rates in by_symbol.items():
            if len(sym_rates) < 2:
                continue
            sorted_rates = sorted(sym_rates, key=lambda x: x.rate)
            lowest = sorted_rates[0]
            highest = sorted_rates[-1]
            spread = highest.annualized - lowest.annualized
            if spread >= min_spread:
                opportunities.append(FundingArbitrage(
                    symbol=symbol,
                    long_exchange=lowest.exchange,
                    short_exchange=highest.exchange,
                    spread=round(spread, 4),
                    long_rate=lowest.annualized,
                    short_rate=highest.annualized,
                ))
        return sorted(opportunities, key=lambda x: x.spread, reverse=True)

    def _fetch_binance(self, symbols: list[str]) -> list[FundingRate]:
        """Fetch funding rates from Binance Futures."""
        rates = []
        try:
            data = self._binance.get("/fapi/v1/premiumIndex")
            if isinstance(data, list):
                sym_set = {s.upper() for s in symbols}
                for item in data:
                    sym = item.get("symbol", "")
                    if sym in sym_set:
                        rate = float(item.get("lastFundingRate", 0))
                        rates.append(FundingRate(
                            exchange="binance",
                            symbol=sym,
                            rate=rate,
                            annualized=_annualize_8h_rate(rate),
                            next_funding_time=int(item.get("nextFundingTime", 0)),
                        ))
        except (ExchangeAPIError, ExchangeConnectionError, Exception):
            rates.extend(self._simulated_rates("binance", symbols))
        return rates

    def _fetch_bybit(self, symbols: list[str]) -> list[FundingRate]:
        """Fetch funding rates from Bybit."""
        rates = []
        for symbol in symbols:
            try:
                data = self._bybit.get("/v5/market/tickers", params={"category": "linear", "symbol": symbol})
                result_list = data.get("result", {}).get("list", [])
                for item in result_list:
                    rate = float(item.get("fundingRate", 0))
                    rates.append(FundingRate(
                        exchange="bybit",
                        symbol=symbol,
                        rate=rate,
                        annualized=_annualize_8h_rate(rate),
                    ))
            except (ExchangeAPIError, ExchangeConnectionError, Exception):
                rates.extend(self._simulated_rates("bybit", [symbol]))
        return rates

    def _fetch_okx(self, symbols: list[str]) -> list[FundingRate]:
        """Fetch funding rates from OKX."""
        rates = []
        # OKX uses different symbol format: BTC-USDT-SWAP
        okx_map = {}
        for s in symbols:
            base = s.replace("USDT", "")
            okx_sym = f"{base}-USDT-SWAP"
            okx_map[okx_sym] = s

        for okx_sym, orig_sym in okx_map.items():
            try:
                data = self._okx.get("/api/v5/public/funding-rate", params={"instId": okx_sym})
                for item in data.get("data", []):
                    rate = float(item.get("fundingRate", 0))
                    rates.append(FundingRate(
                        exchange="okx",
                        symbol=orig_sym,
                        rate=rate,
                        annualized=_annualize_8h_rate(rate),
                        next_funding_time=int(item.get("nextFundingTime", 0)),
                    ))
            except (ExchangeAPIError, ExchangeConnectionError, Exception):
                rates.extend(self._simulated_rates("okx", [orig_sym]))
        return rates

    @staticmethod
    def _simulated_rates(exchange: str, symbols: list[str]) -> list[FundingRate]:
        """Generate simulated funding rates for fallback."""
        import hashlib
        rates = []
        for sym in symbols:
            h = int(hashlib.sha256(f"{exchange}:{sym}".encode()).hexdigest()[:8], 16)
            rate = (h % 200 - 50) / 1_000_000  # -0.005% to 0.015%
            rates.append(FundingRate(
                exchange=exchange,
                symbol=sym,
                rate=rate,
                annualized=_annualize_8h_rate(rate),
            ))
        return rates
