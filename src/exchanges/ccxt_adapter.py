"""
CCXT Universal Exchange Adapter
Supports 100+ crypto exchanges through ccxt library.
"""

from typing import Optional, List, Dict, Any

try:
    import ccxt as _ccxt
    HAS_CCXT = True
except ImportError:
    _ccxt = None
    HAS_CCXT = False

SUPPORTED_EXCHANGES = [
    'binance', 'coinbase', 'kraken', 'okx', 'bybit',
    'bitget', 'gate', 'kucoin', 'huobi', 'mexc',
]


class CCXTAdapter:
    """Universal crypto exchange adapter powered by ccxt."""

    def __init__(self, exchange_id: str = 'binance', config: dict = None):
        if not HAS_CCXT:
            raise ImportError(
                "ccxt is not installed. Install it with: pip install ccxt"
            )
        if exchange_id not in _ccxt.exchanges:
            raise ValueError(
                f"Exchange '{exchange_id}' not supported. "
                f"Available: {_ccxt.exchanges[:10]}..."
            )
        ExchangeClass = getattr(_ccxt, exchange_id)
        self.exchange = ExchangeClass(config or {})
        self.exchange_id = exchange_id

    def get_ticker(self, symbol: str) -> dict:
        """Get real-time ticker. symbol format: 'BTC/USDT'"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                'symbol': symbol,
                'price': ticker.get('last'),
                'change_pct': ticker.get('percentage'),
                'volume': ticker.get('quoteVolume'),
                'high': ticker.get('high'),
                'low': ticker.get('low'),
                'bid': ticker.get('bid'),
                'ask': ticker.get('ask'),
            }
        except Exception as e:
            return {'error': str(e)}

    def get_ohlcv(self, symbol: str, timeframe: str = '1d', limit: int = 100) -> list:
        """Get OHLCV candles. timeframe: '1m','5m','1h','1d','1w'"""
        try:
            data = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            return [
                {
                    'timestamp': d[0],
                    'open': d[1],
                    'high': d[2],
                    'low': d[3],
                    'close': d[4],
                    'volume': d[5],
                }
                for d in data
            ]
        except Exception as e:
            return []

    def get_orderbook(self, symbol: str, limit: int = 20) -> dict:
        """Get order book depth."""
        try:
            return self.exchange.fetch_order_book(symbol, limit)
        except Exception as e:
            return {'error': str(e)}

    def list_markets(self) -> list:
        """List all available trading pairs."""
        try:
            self.exchange.load_markets()
            return list(self.exchange.markets.keys())
        except Exception:
            return []

    @staticmethod
    def list_exchanges() -> list:
        """List all supported exchanges."""
        if not HAS_CCXT:
            return []
        return _ccxt.exchanges
