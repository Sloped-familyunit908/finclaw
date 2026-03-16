"""
Tests for WebSocket real-time data modules — v4.1.0
40+ tests covering ws_client, binance_ws, okx_ws, bybit_ws, data_aggregator, market_store.
"""

import asyncio
import json
import os
import tempfile
import time
import pytest

from src.exchanges.ws_client import WebSocketClient
from src.exchanges.binance_ws import BinanceWebSocket, SPOT_WS, FUTURES_WS
from src.exchanges.okx_ws import OKXWebSocket
from src.exchanges.bybit_ws import BybitWebSocket
from src.exchanges.data_aggregator import DataAggregator
from src.data.market_store import MarketStore


# ============================================================
# WebSocketClient tests
# ============================================================

class TestWebSocketClient:
    def test_init_defaults(self):
        ws = WebSocketClient("wss://example.com/ws")
        assert ws.url == "wss://example.com/ws"
        assert ws.connected is False
        assert ws.subscriptions == []
        assert ws.callbacks == {}
        assert ws.reconnect is True
        assert ws.max_reconnect_attempts == 5

    def test_init_custom_params(self):
        ws = WebSocketClient("wss://x.com", reconnect=False, max_reconnect_attempts=3, ping_interval=10.0)
        assert ws.reconnect is False
        assert ws.max_reconnect_attempts == 3
        assert ws.ping_interval == 10.0

    def test_on_registers_callback(self):
        ws = WebSocketClient("wss://x.com")
        calls = []
        ws.on("message", lambda d: calls.append(d))
        assert len(ws.callbacks["message"]) == 1

    def test_on_multiple_callbacks(self):
        ws = WebSocketClient("wss://x.com")
        ws.on("message", lambda d: None)
        ws.on("message", lambda d: None)
        ws.on("connected", lambda d: None)
        assert len(ws.callbacks["message"]) == 2
        assert len(ws.callbacks["connected"]) == 1

    def test_off_removes_callback(self):
        ws = WebSocketClient("wss://x.com")
        cb = lambda d: None
        ws.on("message", cb)
        ws.off("message", cb)
        assert len(ws.callbacks["message"]) == 0

    def test_off_removes_all(self):
        ws = WebSocketClient("wss://x.com")
        ws.on("test", lambda d: None)
        ws.on("test", lambda d: None)
        ws.off("test")
        assert "test" not in ws.callbacks

    def test_emit_fires_callbacks(self):
        ws = WebSocketClient("wss://x.com")
        results = []
        ws.on("evt", lambda d: results.append(d))
        ws._emit("evt", {"key": "val"})
        assert results == [{"key": "val"}]

    def test_emit_handles_callback_error(self):
        ws = WebSocketClient("wss://x.com")
        ws.on("evt", lambda d: 1 / 0)  # raises
        ws._emit("evt", {})  # should not raise

    def test_last_message_time_initially_zero(self):
        ws = WebSocketClient("wss://x.com")
        assert ws.last_message_time == 0

    def test_subscribe_stores_subscription(self):
        ws = WebSocketClient("wss://x.com")
        ws._connected = False
        asyncio.run(ws.subscribe("ticker", "BTCUSDT"))
        assert len(ws.subscriptions) == 1
        assert ws.subscriptions[0]["channel"] == "ticker"

    def test_unsubscribe_removes(self):
        ws = WebSocketClient("wss://x.com")
        asyncio.run(ws.subscribe("ticker", "BTCUSDT"))
        asyncio.run(ws.unsubscribe("ticker", "BTCUSDT"))
        assert len(ws.subscriptions) == 0

    def test_send_raises_when_not_connected(self):
        ws = WebSocketClient("wss://x.com")
        with pytest.raises(ConnectionError):
            asyncio.run(ws.send({"test": 1}))

    def test_close_sets_state(self):
        ws = WebSocketClient("wss://x.com")
        ws._running = True
        asyncio.run(ws.close())
        assert ws._running is False
        assert ws.connected is False


# ============================================================
# BinanceWebSocket tests
# ============================================================

class TestBinanceWebSocket:
    def test_init_spot(self):
        ws = BinanceWebSocket(futures=False)
        assert ws.url == SPOT_WS
        assert ws.futures is False

    def test_init_futures(self):
        ws = BinanceWebSocket(futures=True)
        assert ws.url == FUTURES_WS
        assert ws.futures is True

    def test_build_stream_ticker(self):
        ws = BinanceWebSocket()
        assert ws._build_stream("ticker", "BTCUSDT", {}) == "btcusdt@ticker"

    def test_build_stream_kline(self):
        ws = BinanceWebSocket()
        assert ws._build_stream("kline", "ETHUSDT", {"interval": "5m"}) == "ethusdt@kline_5m"

    def test_build_stream_kline_default(self):
        ws = BinanceWebSocket()
        assert ws._build_stream("kline", "ETHUSDT", {}) == "ethusdt@kline_1m"

    def test_build_stream_orderbook(self):
        ws = BinanceWebSocket()
        assert ws._build_stream("orderbook", "BTCUSDT", {"depth": 10}) == "btcusdt@depth10@100ms"

    def test_build_stream_trades(self):
        ws = BinanceWebSocket()
        assert ws._build_stream("trades", "BTCUSDT", {}) == "btcusdt@trade"

    def test_build_stream_custom(self):
        ws = BinanceWebSocket()
        assert ws._build_stream("miniTicker", "BTCUSDT", {}) == "btcusdt@miniTicker"

    def test_parse_ticker(self):
        data = {
            "e": "24hrTicker", "s": "BTCUSDT", "c": "65000.5", "b": "64999",
            "a": "65001", "h": "66000", "l": "64000", "v": "12345.6", "P": "2.5", "E": 1700000000,
        }
        result = BinanceWebSocket.parse_ticker(data)
        assert result["exchange"] == "binance"
        assert result["symbol"] == "BTCUSDT"
        assert result["last"] == 65000.5
        assert result["change_pct"] == 2.5

    def test_parse_ticker_wrong_event(self):
        assert BinanceWebSocket.parse_ticker({"e": "kline"}) is None

    def test_parse_kline(self):
        data = {
            "e": "kline", "k": {
                "s": "BTCUSDT", "i": "1m", "o": "64000", "h": "65000",
                "l": "63900", "c": "64500", "v": "100.5", "t": 1700000000, "x": True,
            }
        }
        result = BinanceWebSocket.parse_kline(data)
        assert result["exchange"] == "binance"
        assert result["close"] == 64500.0
        assert result["closed"] is True

    def test_parse_kline_wrong_event(self):
        assert BinanceWebSocket.parse_kline({"e": "trade"}) is None

    def test_parse_trade(self):
        data = {"e": "trade", "s": "BTCUSDT", "p": "65000", "q": "0.5", "m": True, "T": 170000, "t": 12345}
        result = BinanceWebSocket.parse_trade(data)
        assert result["side"] == "sell"
        assert result["price"] == 65000.0

    def test_parse_trade_buy(self):
        data = {"e": "trade", "s": "ETHUSDT", "p": "3500", "q": "1.0", "m": False, "T": 170000, "t": 99}
        result = BinanceWebSocket.parse_trade(data)
        assert result["side"] == "buy"

    def test_next_id_increments(self):
        ws = BinanceWebSocket()
        assert ws._next_id() == 1
        assert ws._next_id() == 2


# ============================================================
# OKXWebSocket tests
# ============================================================

class TestOKXWebSocket:
    def test_init(self):
        ws = OKXWebSocket()
        assert "okx.com" in ws.url

    def test_build_args_ticker(self):
        ws = OKXWebSocket()
        args = ws._build_args("ticker", "BTC-USDT", {})
        assert args == {"channel": "tickers", "instId": "BTC-USDT"}

    def test_build_args_kline(self):
        ws = OKXWebSocket()
        args = ws._build_args("kline", "BTC-USDT", {"interval": "5m"})
        assert args == {"channel": "candle5m", "instId": "BTC-USDT"}

    def test_build_args_orderbook(self):
        ws = OKXWebSocket()
        args = ws._build_args("orderbook", "BTC-USDT", {"depth": 5})
        assert args == {"channel": "books5", "instId": "BTC-USDT"}

    def test_build_args_trades(self):
        ws = OKXWebSocket()
        args = ws._build_args("trades", "BTC-USDT", {})
        assert args == {"channel": "trades", "instId": "BTC-USDT"}

    def test_parse_ticker(self):
        data = {
            "arg": {"channel": "tickers", "instId": "BTC-USDT"},
            "data": [{"instId": "BTC-USDT", "last": "65000", "bidPx": "64999",
                       "askPx": "65001", "high24h": "66000", "low24h": "64000",
                       "vol24h": "5000", "ts": "1700000000"}],
        }
        result = OKXWebSocket.parse_ticker(data)
        assert result["exchange"] == "okx"
        assert result["last"] == 65000.0

    def test_parse_ticker_wrong_channel(self):
        data = {"arg": {"channel": "trades"}, "data": [{}]}
        assert OKXWebSocket.parse_ticker(data) is None

    def test_parse_ticker_no_data(self):
        data = {"arg": {"channel": "tickers"}, "data": []}
        assert OKXWebSocket.parse_ticker(data) is None

    def test_parse_trade(self):
        data = {
            "arg": {"channel": "trades"},
            "data": [{"instId": "BTC-USDT", "px": "65000", "sz": "0.1", "side": "buy", "ts": "170000", "tradeId": "1"}],
        }
        result = OKXWebSocket.parse_trade(data)
        assert result["exchange"] == "okx"
        assert result["price"] == 65000.0


# ============================================================
# BybitWebSocket tests
# ============================================================

class TestBybitWebSocket:
    def test_init_spot(self):
        ws = BybitWebSocket(category="spot")
        assert "spot" in ws.url

    def test_init_linear(self):
        ws = BybitWebSocket(category="linear")
        assert "linear" in ws.url

    def test_build_topic_ticker(self):
        ws = BybitWebSocket()
        assert ws._build_topic("ticker", "BTCUSDT", {}) == "tickers.BTCUSDT"

    def test_build_topic_kline(self):
        ws = BybitWebSocket()
        assert ws._build_topic("kline", "BTCUSDT", {"interval": "5"}) == "kline.5.BTCUSDT"

    def test_build_topic_orderbook(self):
        ws = BybitWebSocket()
        topic = ws._build_topic("orderbook", "BTCUSDT", {"depth": 5})
        assert topic == "orderbook.1.BTCUSDT"  # snaps to nearest valid: 1

    def test_build_topic_orderbook_50(self):
        ws = BybitWebSocket()
        topic = ws._build_topic("orderbook", "BTCUSDT", {"depth": 40})
        assert topic == "orderbook.50.BTCUSDT"

    def test_build_topic_trades(self):
        ws = BybitWebSocket()
        assert ws._build_topic("trades", "BTCUSDT", {}) == "publicTrade.BTCUSDT"

    def test_parse_ticker(self):
        data = {
            "topic": "tickers.BTCUSDT", "ts": 1700000000,
            "data": {"symbol": "BTCUSDT", "lastPrice": "65000", "bid1Price": "64999",
                     "ask1Price": "65001", "highPrice24h": "66000", "lowPrice24h": "64000",
                     "volume24h": "5000"},
        }
        result = BybitWebSocket.parse_ticker(data)
        assert result["exchange"] == "bybit"
        assert result["last"] == 65000.0

    def test_parse_ticker_wrong_topic(self):
        assert BybitWebSocket.parse_ticker({"topic": "kline.1.BTC", "data": {}}) is None

    def test_parse_trade(self):
        data = {
            "topic": "publicTrade.BTCUSDT",
            "data": [{"s": "BTCUSDT", "p": "65000", "v": "0.5", "S": "Buy", "T": 170000, "i": "abc"}],
        }
        result = BybitWebSocket.parse_trade(data)
        assert result["exchange"] == "bybit"
        assert result["side"] == "buy"

    def test_parse_trade_empty(self):
        data = {"topic": "publicTrade.BTCUSDT", "data": []}
        assert BybitWebSocket.parse_trade(data) is None

    def test_next_req_id(self):
        ws = BybitWebSocket()
        assert ws._next_req_id() == "1"
        assert ws._next_req_id() == "2"


# ============================================================
# DataAggregator tests
# ============================================================

class TestDataAggregator:
    def test_init(self):
        agg = DataAggregator()
        assert agg.feeds == {}
        assert agg._running is False

    def test_add_feed(self):
        agg = DataAggregator()
        agg.add_feed("binance", "BTCUSDT", ["ticker"])
        assert "binance" in agg.feeds
        assert isinstance(agg.feeds["binance"], BinanceWebSocket)

    def test_add_feed_unsupported(self):
        agg = DataAggregator()
        with pytest.raises(ValueError):
            agg.add_feed("kraken", "BTCUSDT", ["ticker"])

    def test_add_multiple_feeds(self):
        agg = DataAggregator()
        agg.add_feed("binance", "BTCUSDT", ["ticker"])
        agg.add_feed("okx", "BTC-USDT", ["ticker"])
        assert len(agg.feeds) == 2

    def test_get_latest_empty(self):
        agg = DataAggregator()
        assert agg.get_latest("binance", "BTCUSDT") == {}

    def test_handle_message_stores(self):
        agg = DataAggregator()
        agg.add_feed("binance", "BTCUSDT", ["ticker"])
        # Simulate a parsed ticker
        data = {
            "e": "24hrTicker", "s": "BTCUSDT", "c": "65000", "b": "64999",
            "a": "65001", "h": "66000", "l": "64000", "v": "1000", "P": "1.5", "E": 170000,
        }
        agg._handle_message("binance", data)
        latest = agg.get_latest("binance", "BTCUSDT")
        assert latest["last"] == 65000.0

    def test_get_spread_single_exchange(self):
        agg = DataAggregator()
        agg._latest = {"binance": {"BTCUSDT": {"last": 65000}}}
        spread = agg.get_spread("BTCUSDT")
        assert spread["spread"] == 0

    def test_get_spread_multiple_exchanges(self):
        agg = DataAggregator()
        agg._latest = {
            "binance": {"BTCUSDT": {"last": 65000}},
            "okx": {"BTCUSDT": {"last": 65100}},
            "bybit": {"BTCUSDT": {"last": 64900}},
        }
        spread = agg.get_spread("BTCUSDT")
        assert spread["spread"] == 200  # 65100 - 64900
        assert spread["low"]["exchange"] == "bybit"
        assert spread["high"]["exchange"] == "okx"
        assert spread["spread_pct"] > 0

    def test_arbitrage_opportunities(self):
        agg = DataAggregator()
        agg._latest = {
            "binance": {"BTCUSDT": {"last": 65000}},
            "okx": {"BTCUSDT": {"last": 65200}},
        }
        opps = agg.get_arbitrage_opportunities(min_spread_pct=0.01)
        assert len(opps) == 1
        assert opps[0]["symbol"] == "BTCUSDT"

    def test_arbitrage_no_opportunities(self):
        agg = DataAggregator()
        agg._latest = {
            "binance": {"BTCUSDT": {"last": 65000}},
            "okx": {"BTCUSDT": {"last": 65000}},
        }
        opps = agg.get_arbitrage_opportunities(min_spread_pct=0.1)
        assert len(opps) == 0

    def test_on_update_callback(self):
        agg = DataAggregator()
        agg.add_feed("binance", "BTCUSDT", ["ticker"])
        updates = []
        agg.on_update(lambda ex, sym, d: updates.append((ex, sym)))
        data = {"e": "24hrTicker", "s": "BTCUSDT", "c": "65000", "b": "0", "a": "0", "h": "0", "l": "0", "v": "0", "P": "0", "E": 0}
        agg._handle_message("binance", data)
        assert len(updates) == 1

    def test_connected_exchanges_empty(self):
        agg = DataAggregator()
        assert agg.connected_exchanges == []


# ============================================================
# MarketStore tests
# ============================================================

class TestMarketStore:
    def test_init(self):
        store = MarketStore()
        assert store.stats["ticks_in_memory"] == 0
        assert store.stats["candles_in_memory"] == 0

    def test_store_tick(self):
        store = MarketStore()
        store.store_tick("binance", "BTCUSDT", {"price": 65000, "volume": 1.5})
        ticks = store.get_ticks("binance", "BTCUSDT")
        assert len(ticks) == 1
        assert ticks[0]["price"] == 65000

    def test_store_tick_max_limit(self):
        store = MarketStore(max_ticks=5)
        for i in range(10):
            store.store_tick("binance", "BTCUSDT", {"price": i})
        ticks = store.get_ticks("binance", "BTCUSDT")
        assert len(ticks) == 5
        assert ticks[0]["price"] == 5  # oldest kept

    def test_store_candle(self):
        store = MarketStore()
        store.store_candle("binance", "BTCUSDT", {"timestamp": 1, "open": 64000, "close": 65000})
        candles = store.get_candles("binance", "BTCUSDT")
        assert len(candles) == 1

    def test_store_candle_dedup(self):
        store = MarketStore()
        store.store_candle("binance", "BTCUSDT", {"timestamp": 1, "close": 64000})
        store.store_candle("binance", "BTCUSDT", {"timestamp": 1, "close": 65000})
        candles = store.get_candles("binance", "BTCUSDT")
        assert len(candles) == 1
        assert candles[0]["close"] == 65000

    def test_get_candles_time_range(self):
        store = MarketStore()
        for ts in [100, 200, 300, 400, 500]:
            store.store_candle("binance", "BTC", {"timestamp": ts, "close": ts})
        candles = store.get_candles("binance", "BTC", start=200, end=400)
        assert len(candles) == 3

    def test_get_latest_tick(self):
        store = MarketStore()
        store.store_tick("binance", "BTC", {"price": 1})
        store.store_tick("binance", "BTC", {"price": 2})
        assert store.get_latest_tick("binance", "BTC")["price"] == 2

    def test_get_latest_tick_empty(self):
        store = MarketStore()
        assert store.get_latest_tick("binance", "BTC") is None

    def test_get_latest_candle(self):
        store = MarketStore()
        store.store_candle("x", "Y", {"timestamp": 1, "close": 100})
        store.store_candle("x", "Y", {"timestamp": 2, "close": 200})
        assert store.get_latest_candle("x", "Y")["close"] == 200

    def test_export_csv(self):
        store = MarketStore()
        store.store_candle("binance", "BTC", {"timestamp": 1, "open": 100, "close": 105})
        store.store_candle("binance", "BTC", {"timestamp": 2, "open": 105, "close": 110})
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        try:
            rows = store.export_csv("binance", "BTC", path, data_type="candles")
            assert rows == 2
            with open(path) as f:
                lines = f.readlines()
            assert len(lines) == 3  # header + 2 rows
            assert "timestamp" in lines[0]
        finally:
            os.unlink(path)

    def test_export_csv_empty(self):
        store = MarketStore()
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        try:
            rows = store.export_csv("binance", "BTC", path)
            assert rows == 0
        finally:
            os.unlink(path)

    def test_export_ticks_csv(self):
        store = MarketStore()
        store.store_tick("okx", "ETH", {"price": 3500, "vol": 10})
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        try:
            rows = store.export_csv("okx", "ETH", path, data_type="ticks")
            assert rows == 1
        finally:
            os.unlink(path)

    def test_save_snapshot(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MarketStore(data_dir=tmpdir)
            store.store_tick("binance", "BTC", {"price": 65000})
            path = store.save_snapshot("binance", "BTC")
            assert path is not None
            with open(path) as f:
                data = json.load(f)
            assert data["exchange"] == "binance"
            assert len(data["ticks"]) == 1

    def test_save_snapshot_no_dir(self):
        store = MarketStore()
        assert store.save_snapshot("x", "y") is None

    def test_clear_specific(self):
        store = MarketStore()
        store.store_tick("binance", "BTC", {"price": 1})
        store.store_tick("binance", "ETH", {"price": 2})
        store.clear("binance", "BTC")
        assert store.get_ticks("binance", "BTC") == []
        assert len(store.get_ticks("binance", "ETH")) == 1

    def test_clear_exchange(self):
        store = MarketStore()
        store.store_tick("binance", "BTC", {"price": 1})
        store.store_tick("okx", "BTC", {"price": 2})
        store.clear("binance")
        assert store.get_ticks("binance", "BTC") == []
        assert len(store.get_ticks("okx", "BTC")) == 1

    def test_clear_all(self):
        store = MarketStore()
        store.store_tick("binance", "BTC", {"price": 1})
        store.store_tick("okx", "ETH", {"price": 2})
        store.clear()
        assert store.stats["ticks_in_memory"] == 0

    def test_stats(self):
        store = MarketStore()
        store.store_tick("a", "b", {"x": 1})
        store.store_candle("a", "b", {"timestamp": 1})
        stats = store.stats
        assert stats["ticks_stored"] == 1
        assert stats["candles_stored"] == 1
        assert stats["ticks_in_memory"] == 1
        assert stats["candles_in_memory"] == 1

    def test_get_ticks_with_limit(self):
        store = MarketStore()
        for i in range(20):
            store.store_tick("x", "y", {"price": i})
        assert len(store.get_ticks("x", "y", limit=5)) == 5
        assert store.get_ticks("x", "y", limit=5)[0]["price"] == 15
