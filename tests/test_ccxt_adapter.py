"""Tests for CCXT universal exchange adapter."""

import pytest
from unittest.mock import MagicMock, patch


class TestCCXTAdapterInit:
    """Test CCXTAdapter initialization."""

    def test_import_guard(self):
        """CCXTAdapter module should import without error."""
        from src.exchanges.ccxt_adapter import CCXTAdapter, HAS_CCXT
        assert HAS_CCXT is True  # ccxt is installed in this environment

    def test_list_exchanges_returns_non_empty(self):
        """list_exchanges() should return a non-empty list."""
        from src.exchanges.ccxt_adapter import CCXTAdapter
        exchanges = CCXTAdapter.list_exchanges()
        assert isinstance(exchanges, list)
        assert len(exchanges) > 50  # ccxt supports 100+ exchanges
        assert 'binance' in exchanges

    def test_init_default_exchange(self):
        """Should initialize with default exchange (binance)."""
        from src.exchanges.ccxt_adapter import CCXTAdapter
        adapter = CCXTAdapter()
        assert adapter.exchange_id == 'binance'
        assert adapter.exchange is not None

    def test_init_custom_exchange(self):
        """Should initialize with a custom exchange."""
        from src.exchanges.ccxt_adapter import CCXTAdapter
        adapter = CCXTAdapter(exchange_id='kraken')
        assert adapter.exchange_id == 'kraken'

    def test_init_invalid_exchange_raises(self):
        """Should raise ValueError for unsupported exchange."""
        from src.exchanges.ccxt_adapter import CCXTAdapter
        with pytest.raises(ValueError, match="not supported"):
            CCXTAdapter(exchange_id='not_a_real_exchange_xyz')

    def test_init_with_config(self):
        """Should pass config to the exchange constructor."""
        from src.exchanges.ccxt_adapter import CCXTAdapter
        adapter = CCXTAdapter(exchange_id='binance', config={'timeout': 30000})
        assert adapter.exchange.timeout == 30000


class TestCCXTAdapterMocked:
    """Test CCXTAdapter methods with mocked ccxt exchange."""

    def test_get_ticker_mocked(self):
        """get_ticker should return normalized ticker data."""
        from src.exchanges.ccxt_adapter import CCXTAdapter
        adapter = CCXTAdapter(exchange_id='binance')

        mock_ticker = {
            'symbol': 'BTC/USDT',
            'last': 67500.0,
            'percentage': 2.5,
            'quoteVolume': 1_500_000_000,
            'high': 68000.0,
            'low': 66000.0,
            'bid': 67490.0,
            'ask': 67510.0,
        }
        adapter.exchange.fetch_ticker = MagicMock(return_value=mock_ticker)

        result = adapter.get_ticker('BTC/USDT')
        assert result['symbol'] == 'BTC/USDT'
        assert result['price'] == 67500.0
        assert result['change_pct'] == 2.5
        assert result['volume'] == 1_500_000_000
        assert result['high'] == 68000.0
        assert result['low'] == 66000.0
        assert result['bid'] == 67490.0
        assert result['ask'] == 67510.0

    def test_get_ticker_error_returns_error_dict(self):
        """get_ticker should return error dict on failure."""
        from src.exchanges.ccxt_adapter import CCXTAdapter
        adapter = CCXTAdapter(exchange_id='binance')
        adapter.exchange.fetch_ticker = MagicMock(side_effect=Exception("Network error"))

        result = adapter.get_ticker('BTC/USDT')
        assert 'error' in result

    def test_get_ohlcv_mocked(self):
        """get_ohlcv should return list of candle dicts."""
        from src.exchanges.ccxt_adapter import CCXTAdapter
        adapter = CCXTAdapter(exchange_id='binance')

        mock_data = [
            [1700000000000, 67000, 68000, 66500, 67500, 1000],
            [1700086400000, 67500, 69000, 67000, 68500, 1200],
        ]
        adapter.exchange.fetch_ohlcv = MagicMock(return_value=mock_data)

        result = adapter.get_ohlcv('BTC/USDT', '1d', 2)
        assert len(result) == 2
        assert result[0]['open'] == 67000
        assert result[0]['close'] == 67500
        assert result[1]['volume'] == 1200

    def test_get_ohlcv_error_returns_empty(self):
        """get_ohlcv should return empty list on failure."""
        from src.exchanges.ccxt_adapter import CCXTAdapter
        adapter = CCXTAdapter(exchange_id='binance')
        adapter.exchange.fetch_ohlcv = MagicMock(side_effect=Exception("Timeout"))

        result = adapter.get_ohlcv('BTC/USDT')
        assert result == []

    def test_get_orderbook_mocked(self):
        """get_orderbook should return order book data."""
        from src.exchanges.ccxt_adapter import CCXTAdapter
        adapter = CCXTAdapter(exchange_id='binance')

        mock_book = {'bids': [[67490, 1.5]], 'asks': [[67510, 2.0]]}
        adapter.exchange.fetch_order_book = MagicMock(return_value=mock_book)

        result = adapter.get_orderbook('BTC/USDT')
        assert 'bids' in result
        assert 'asks' in result

    def test_list_markets_mocked(self):
        """list_markets should return list of trading pairs."""
        from src.exchanges.ccxt_adapter import CCXTAdapter
        adapter = CCXTAdapter(exchange_id='binance')
        adapter.exchange.load_markets = MagicMock()
        adapter.exchange.markets = {'BTC/USDT': {}, 'ETH/USDT': {}}

        result = adapter.list_markets()
        assert 'BTC/USDT' in result
        assert 'ETH/USDT' in result
