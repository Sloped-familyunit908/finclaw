# Exchanges

FinClaw supports 12 exchange adapters across crypto, US equities, and China A-shares. All adapters implement a common interface: `get_ticker()`, `get_ohlcv()`, and market-specific methods.

---

## Exchange Overview

| Exchange | Type | Module | Auth Required | WebSocket |
|---|---|---|---|---|
| Yahoo Finance | US/Global Stocks | `yahoo_finance` | No | No |
| Polygon | US Stocks | `polygon` | Yes (API key) | No |
| Alpha Vantage | US/Global Stocks | `alpha_vantage` | Yes (API key) | No |
| AkShare | China A-Shares | `akshare_adapter` | No | No |
| BaoStock | China A-Shares | `baostock_adapter` | No | No |
| Tushare | China A-Shares | `tushare_adapter` | Yes (token) | No |
| Binance | Crypto | `binance` | Yes (API key) | Yes |
| Bybit | Crypto | `bybit` | Yes (API key) | Yes |
| OKX | Crypto | `okx` | Yes (API key) | Yes |
| Coinbase | Crypto | `coinbase` | Yes (API key) | No |
| Kraken | Crypto | `kraken` | Yes (API key) | No |
| Alpaca | US Stocks | `alpaca` | Yes (API key) | No |

---

## US / Global Stock Exchanges

### Yahoo Finance (Default)

No API key required. Best for getting started.

```python
from src.exchanges.registry import ExchangeRegistry

yahoo = ExchangeRegistry.get("yahoo")
quote = yahoo.get_ticker("AAPL")
candles = yahoo.get_ohlcv("AAPL", "1d", limit=50)
```

```bash
# CLI
python finclaw.py signal --ticker AAPL --strategy momentum
```

### Polygon

High-quality US market data. Free tier available at [polygon.io](https://polygon.io).

**Setup:**

```bash
export POLYGON_API_KEY="your_key_here"
```

```python
polygon = ExchangeRegistry.get("polygon")
quote = polygon.get_ticker("MSFT")
```

### Alpha Vantage

Free tier: 25 requests/day. Get a key at [alphavantage.co](https://www.alphavantage.co/support/#api-key).

```bash
export ALPHA_VANTAGE_API_KEY="your_key_here"
```

```python
av = ExchangeRegistry.get("alpha_vantage")
quote = av.get_ticker("GOOGL")
```

### Alpaca

Paper and live trading via [alpaca.markets](https://alpaca.markets).

```bash
export ALPACA_API_KEY="your_key"
export ALPACA_SECRET_KEY="your_secret"
export ALPACA_BASE_URL="https://paper-api.alpaca.markets"  # paper trading
```

---

## China A-Shares

### AkShare

Open-source China market data. No API key needed.

```python
akshare = ExchangeRegistry.get("akshare")
quote = akshare.get_ticker("000001.SZ")  # Ping An Bank
candles = akshare.get_ohlcv("600519.SH", "1d", limit=100)  # Moutai
```

```bash
python finclaw.py scan --market china --style buffett
```

### BaoStock

Another free China data source with good historical coverage.

```python
baostock = ExchangeRegistry.get("baostock")
candles = baostock.get_ohlcv("sh.600000", "1d", limit=200)
```

### Tushare

Professional China market data. Get a token at [tushare.pro](https://tushare.pro).

```bash
export TUSHARE_TOKEN="your_token_here"
```

```python
tushare = ExchangeRegistry.get("tushare")
quote = tushare.get_ticker("000001.SZ")
```

---

## Crypto Exchanges

### Binance

The largest crypto exchange by volume. Supports WebSocket streaming.

```bash
export BINANCE_API_KEY="your_key"
export BINANCE_API_SECRET="your_secret"
```

```python
binance = ExchangeRegistry.get("binance")
quote = binance.get_ticker("BTCUSDT")
candles = binance.get_ohlcv("ETHUSDT", "1h", limit=100)
```

**WebSocket streaming:**

```python
from src.exchanges.binance_ws import BinanceWebSocket

ws = BinanceWebSocket()
ws.subscribe("BTCUSDT", callback=on_tick)
ws.start()
```

### Bybit

Derivatives-focused exchange with WebSocket support.

```bash
export BYBIT_API_KEY="your_key"
export BYBIT_API_SECRET="your_secret"
```

```python
bybit = ExchangeRegistry.get("bybit")
quote = bybit.get_ticker("BTCUSDT")
```

### OKX

Full-featured crypto exchange with WebSocket.

```bash
export OKX_API_KEY="your_key"
export OKX_API_SECRET="your_secret"
export OKX_PASSPHRASE="your_passphrase"
```

```python
okx = ExchangeRegistry.get("okx")
quote = okx.get_ticker("BTC-USDT")
```

### Coinbase

US-regulated crypto exchange.

```bash
export COINBASE_API_KEY="your_key"
export COINBASE_API_SECRET="your_secret"
```

### Kraken

European crypto exchange with strong security reputation.

```bash
export KRAKEN_API_KEY="your_key"
export KRAKEN_API_SECRET="your_secret"
```

---

## Data Aggregator

Combine multiple sources for resilience and quality:

```python
from src.exchanges.data_aggregator import DataAggregator

agg = DataAggregator(sources=["yahoo", "polygon", "alpha_vantage"])
quote = agg.get_best_quote("AAPL")  # Uses the freshest available
```

---

## Exchange Registry

List all available exchanges programmatically:

```python
from src.exchanges.registry import ExchangeRegistry

# List by type
ExchangeRegistry.list_by_type("crypto")    # ['binance', 'bybit', 'okx', ...]
ExchangeRegistry.list_by_type("stock_us")  # ['yahoo', 'polygon', ...]
ExchangeRegistry.list_by_type("stock_cn")  # ['akshare', 'baostock', ...]
```

---

## Adding a New Exchange

See [Plugins → Exchange Plugins](plugins.md#exchange-plugins) for how to create custom exchange adapters.
