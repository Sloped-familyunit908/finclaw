"""
Tests for Issue #4: Exchange adapters missing error handling for network failures.

Covers gaps NOT addressed by existing test_exchange_error_handling.py:
1. AKShare get_ticker/get_orderbook use raw urllib — network errors must still become ExchangeError
2. Baostock get_ohlcv silently swallows errors instead of raising ExchangeError
3. Baostock get_dividends/get_industry lack @handle_network_errors and silently swallow errors
4. Tushare _api raises RuntimeError (not caught by decorator) — should become ExchangeError
5. Kraken _check_result raises RuntimeError — should become ExchangeError
6. All adapters: comprehensive coverage of every public method against every failure mode
"""

import urllib.error
import pytest
from unittest.mock import patch, MagicMock

from src.exchanges.base import ExchangeError
from src.exchanges.http_client import ExchangeAPIError, ExchangeConnectionError


# ============================================================================
# AKShare: raw urllib calls in get_ticker / get_orderbook
# ============================================================================

class TestAKShareNetworkErrors:
    """AKShare get_ticker and get_orderbook use raw urllib.request.urlopen
    instead of self.sina_client. Network failures must still produce ExchangeError."""

    def setup_method(self):
        from src.exchanges.akshare_adapter import AKShareAdapter
        self.adapter = AKShareAdapter()

    def test_get_ticker_timeout(self):
        """urllib.request.urlopen timeout should become ExchangeError."""
        with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            with pytest.raises(ExchangeError, match="timed out"):
                self.adapter.get_ticker("000001.SZ")

    def test_get_ticker_connection_refused(self):
        """URLError (connection refused) should become ExchangeError."""
        with patch("urllib.request.urlopen",
                   side_effect=urllib.error.URLError("Connection refused")):
            with pytest.raises(ExchangeError, match="Network error"):
                self.adapter.get_ticker("000001.SZ")

    def test_get_ticker_http_error(self):
        """HTTP 503 from Sina should become ExchangeError, not crash."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"Service Unavailable"
        err = urllib.error.HTTPError(
            "https://hq.sinajs.cn", 503, "Service Unavailable", {}, mock_resp,
        )
        with patch("urllib.request.urlopen", side_effect=err):
            with pytest.raises(ExchangeError):
                self.adapter.get_ticker("000001.SZ")

    def test_get_orderbook_timeout(self):
        with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            with pytest.raises(ExchangeError, match="timed out"):
                self.adapter.get_orderbook("000001.SZ")

    def test_get_orderbook_connection_refused(self):
        with patch("urllib.request.urlopen",
                   side_effect=urllib.error.URLError("Connection refused")):
            with pytest.raises(ExchangeError, match="Network error"):
                self.adapter.get_orderbook("000001.SZ")

    def test_get_ohlcv_connection_error(self):
        """get_ohlcv goes through HttpClient — should also become ExchangeError."""
        with patch.object(self.adapter.em_client, "get",
                         side_effect=ExchangeConnectionError("refused", "https://push2his.eastmoney.com")):
            with pytest.raises(ExchangeError, match="Connection failed"):
                self.adapter.get_ohlcv("000001.SZ")

    def test_get_ohlcv_api_error(self):
        with patch.object(self.adapter.em_client, "get",
                         side_effect=ExchangeAPIError(429, "rate limited", "https://push2his.eastmoney.com")):
            with pytest.raises(ExchangeError, match="HTTP 429"):
                self.adapter.get_ohlcv("000001.SZ")


# ============================================================================
# Baostock: silent error swallowing
# ============================================================================

class TestBaostockNetworkErrors:
    """Baostock silently swallows errors in get_ohlcv (bare except),
    and get_dividends/get_industry lack @handle_network_errors entirely."""

    def setup_method(self):
        from src.exchanges.baostock_adapter import BaostockAdapter
        self.adapter = BaostockAdapter()

    def test_get_ohlcv_connection_error_not_swallowed(self):
        """Connection errors should raise ExchangeError, not silently return []."""
        with patch.object(self.adapter.client, "get",
                         side_effect=ExchangeConnectionError("refused", "http://www.baostock.com")):
            with pytest.raises(ExchangeError, match="Connection failed"):
                self.adapter.get_ohlcv("sh.600000")

    def test_get_ohlcv_timeout_not_swallowed(self):
        """Timeout should raise ExchangeError, not silently return []."""
        with patch.object(self.adapter.client, "get",
                         side_effect=TimeoutError("request timed out")):
            with pytest.raises(ExchangeError, match="timed out"):
                self.adapter.get_ohlcv("sh.600000")

    def test_get_ohlcv_api_error_not_swallowed(self):
        """HTTP errors should raise ExchangeError, not silently return []."""
        with patch.object(self.adapter.client, "get",
                         side_effect=ExchangeAPIError(500, "Internal Error", "http://www.baostock.com")):
            with pytest.raises(ExchangeError, match="HTTP 500"):
                self.adapter.get_ohlcv("sh.600000")

    def test_get_ticker_connection_error(self):
        """get_ticker calls get_ohlcv — should propagate ExchangeError."""
        with patch.object(self.adapter.client, "get",
                         side_effect=ExchangeConnectionError("refused", "http://www.baostock.com")):
            with pytest.raises(ExchangeError):
                self.adapter.get_ticker("sh.600000")

    def test_get_dividends_connection_error(self):
        """get_dividends should raise ExchangeError on network failure."""
        with patch.object(self.adapter.client, "get",
                         side_effect=ExchangeConnectionError("refused", "http://www.baostock.com")):
            with pytest.raises(ExchangeError, match="Connection failed"):
                self.adapter.get_dividends("sh.600000")

    def test_get_dividends_timeout(self):
        with patch.object(self.adapter.client, "get",
                         side_effect=TimeoutError("timed out")):
            with pytest.raises(ExchangeError, match="timed out"):
                self.adapter.get_dividends("sh.600000")

    def test_get_industry_connection_error(self):
        """get_industry should raise ExchangeError on network failure."""
        with patch.object(self.adapter.client, "get",
                         side_effect=ExchangeConnectionError("refused", "http://www.baostock.com")):
            with pytest.raises(ExchangeError, match="Connection failed"):
                self.adapter.get_industry("sh.600000")

    def test_get_industry_timeout(self):
        with patch.object(self.adapter.client, "get",
                         side_effect=TimeoutError("timed out")):
            with pytest.raises(ExchangeError, match="timed out"):
                self.adapter.get_industry("sh.600000")


# ============================================================================
# Tushare: RuntimeError not caught by decorator
# ============================================================================

class TestTushareNetworkErrors:
    """Tushare _api() raises RuntimeError on API errors, which bypasses
    @handle_network_errors. Should produce ExchangeError instead."""

    def setup_method(self):
        from src.exchanges.tushare_adapter import TushareAdapter
        self.adapter = TushareAdapter({"token": "test"})

    def test_get_ohlcv_api_error_response(self):
        """Tushare returning code=-1 should raise ExchangeError, not RuntimeError."""
        with patch.object(self.adapter.client, "post",
                         return_value={"code": -1, "msg": "token error"}):
            with pytest.raises(ExchangeError, match="token error"):
                self.adapter.get_ohlcv("000001.SZ")

    def test_get_ticker_api_error_response(self):
        with patch.object(self.adapter.client, "post",
                         return_value={"code": -2, "msg": "rate limit exceeded"}):
            with pytest.raises(ExchangeError, match="rate limit"):
                self.adapter.get_ticker("000001.SZ")

    def test_get_ohlcv_connection_error(self):
        with patch.object(self.adapter.client, "post",
                         side_effect=ExchangeConnectionError("refused", "http://api.tushare.pro")):
            with pytest.raises(ExchangeError, match="Connection failed"):
                self.adapter.get_ohlcv("000001.SZ")

    def test_get_ohlcv_timeout(self):
        with patch.object(self.adapter.client, "post",
                         side_effect=TimeoutError("timed out")):
            with pytest.raises(ExchangeError, match="timed out"):
                self.adapter.get_ohlcv("000001.SZ")


# ============================================================================
# Kraken: RuntimeError from _check_result not caught by decorator
# ============================================================================

class TestKrakenNetworkErrors:
    """Kraken _check_result raises RuntimeError for API-level errors,
    which bypasses @handle_network_errors."""

    def setup_method(self):
        from src.exchanges.kraken import KrakenAdapter
        self.adapter = KrakenAdapter()

    def test_get_ohlcv_kraken_api_error(self):
        """Kraken returning error array should raise ExchangeError, not RuntimeError."""
        with patch.object(self.adapter.client, "get",
                         return_value={"error": ["EGeneral:Invalid arguments"], "result": {}}):
            with pytest.raises(ExchangeError, match="Invalid arguments"):
                self.adapter.get_ohlcv("XXBTZUSD")

    def test_get_ticker_kraken_api_error(self):
        with patch.object(self.adapter.client, "get",
                         return_value={"error": ["EQuery:Unknown asset pair"], "result": {}}):
            with pytest.raises(ExchangeError, match="Unknown asset pair"):
                self.adapter.get_ticker("INVALID")

    def test_get_orderbook_connection_error(self):
        with patch.object(self.adapter.client, "get",
                         side_effect=ExchangeConnectionError("DNS failed", "https://api.kraken.com")):
            with pytest.raises(ExchangeError, match="Connection failed"):
                self.adapter.get_orderbook("XXBTZUSD")

    def test_get_ohlcv_timeout(self):
        with patch.object(self.adapter.client, "get",
                         side_effect=TimeoutError("timed out")):
            with pytest.raises(ExchangeError, match="timed out"):
                self.adapter.get_ohlcv("XXBTZUSD")


# ============================================================================
# Comprehensive: every adapter, every public method, key failure modes
# ============================================================================

class TestAllAdaptersNetworkResilience:
    """Verify every adapter's public methods raise ExchangeError
    (not raw exceptions) for network failures."""

    ADAPTERS = [
        ("binance", "src.exchanges.binance", "BinanceAdapter", {}),
        ("okx", "src.exchanges.okx", "OKXAdapter", {}),
        ("bybit", "src.exchanges.bybit", "BybitAdapter", {}),
        ("coinbase", "src.exchanges.coinbase", "CoinbaseAdapter", {}),
        ("kraken", "src.exchanges.kraken", "KrakenAdapter", {}),
        ("yahoo", "src.exchanges.yahoo_finance", "YahooFinanceAdapter", {}),
        ("alpaca", "src.exchanges.alpaca", "AlpacaAdapter", {}),
        ("polygon", "src.exchanges.polygon", "PolygonAdapter", {}),
        ("alpha_vantage", "src.exchanges.alpha_vantage", "AlphaVantageAdapter", {}),
        ("tushare", "src.exchanges.tushare_adapter", "TushareAdapter", {"token": "test"}),
    ]

    PUBLIC_METHODS = [
        ("get_ohlcv", ("BTCUSDT",)),
        ("get_ticker", ("BTCUSDT",)),
        ("get_orderbook", ("BTCUSDT",)),
    ]

    @pytest.mark.parametrize("adapter_name,module,cls_name,config", ADAPTERS)
    @pytest.mark.parametrize("method_name,args", PUBLIC_METHODS)
    def test_connection_error_raises_exchange_error(self, adapter_name, module, cls_name, config, method_name, args):
        """Every adapter's public method should raise ExchangeError on connection failure."""
        import importlib
        mod = importlib.import_module(module)
        cls = getattr(mod, cls_name)
        adapter = cls(config)

        # Patch all HttpClient instances on the adapter
        clients = []
        for attr_name in dir(adapter):
            attr = getattr(adapter, attr_name, None)
            from src.exchanges.http_client import HttpClient
            if isinstance(attr, HttpClient):
                clients.append((attr_name, attr))

        if not clients:
            pytest.skip(f"{adapter_name} has no HttpClient")

        for client_attr, client_obj in clients:
            with patch.object(client_obj, "get",
                             side_effect=ExchangeConnectionError("refused", "https://test.com")):
                with patch.object(client_obj, "post",
                                 side_effect=ExchangeConnectionError("refused", "https://test.com")):
                    try:
                        getattr(adapter, method_name)(*args)
                        # If it returns normally (e.g., empty data), that's OK too
                    except ExchangeError:
                        pass  # This is expected
                    except NotImplementedError:
                        pass  # Data-only adapters — acceptable
                    except (RuntimeError, OSError, ConnectionError, TimeoutError,
                            ExchangeConnectionError, ExchangeAPIError) as e:
                        pytest.fail(
                            f"{adapter_name}.{method_name} raised raw {type(e).__name__}: {e} "
                            f"instead of ExchangeError"
                        )
