"""Exchange data source — pulls from registered exchange adapters."""

from .base import DataSource


class ExchangeSource(DataSource):
    """Pull data from registered exchange adapters (e.g. Binance, CoinGecko).

    The exchange_adapter must have a method:
        fetch_ohlcv(symbol, start, end) -> list[dict]
    """

    def __init__(self, exchange_adapter, exchange_name: str = "default"):
        self.adapter = exchange_adapter
        self.exchange_name = exchange_name

    def fetch(self, symbols: list[str], start: str, end: str) -> dict[str, list[dict]]:
        result = {}
        for symbol in symbols:
            try:
                rows = self.adapter.fetch_ohlcv(symbol, start, end)
                result[symbol] = rows if rows else []
            except Exception:
                result[symbol] = []
        return result

    def validate(self) -> bool:
        return hasattr(self.adapter, "fetch_ohlcv")
