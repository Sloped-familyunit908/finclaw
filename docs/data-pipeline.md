# Data Pipeline

FinClaw's data pipeline handles multi-source ingestion, caching, validation, and quality checks.

---

## Architecture

```
Data Sources → Multi-Source Aggregator → Validator → Cache → Consumers
```

```
src/pipeline/
├── multi_source.py   # Multi-source data aggregation
├── validator.py      # Data quality checks
└── cache.py          # SQLite-based caching
```

---

## Data Sources

### Price Data

| Source | Coverage | Frequency | Auth |
|---|---|---|---|
| Yahoo Finance | Global equities, crypto, ETFs | 1m - 1mo | Free |
| Polygon | US equities | 1m - 1d | API key |
| Alpha Vantage | Global equities | 1m - 1w | API key |
| AkShare | China A-shares | 1d | Free |
| BaoStock | China A-shares | 5m - 1w | Free |
| Tushare | China A-shares + futures | 1m - 1d | Token |
| Binance | Crypto spot + futures | 1m - 1w | API key |
| Bybit | Crypto derivatives | 1m - 1d | API key |
| OKX | Crypto spot + futures | 1m - 1d | API key |

### Real-Time Streaming

WebSocket connections for live data:

```python
from src.exchanges.binance_ws import BinanceWebSocket

ws = BinanceWebSocket()
ws.subscribe("BTCUSDT", callback=lambda tick: print(tick))
ws.start()
```

Supported: Binance, Bybit, OKX (via `*_ws.py` adapters).

---

## Multi-Source Aggregation

Combine multiple sources for redundancy and best-quality data:

```python
from src.pipeline.multi_source import MultiSourcePipeline

pipeline = MultiSourcePipeline(
    sources=["yahoo", "polygon", "alpha_vantage"],
    fallback_order=["yahoo", "polygon", "alpha_vantage"],
)

# Automatically uses the best available source
data = pipeline.fetch("AAPL", timeframe="1d", limit=200)
```

**Fallback behavior:** If the primary source fails or returns stale data, the pipeline automatically tries the next source.

---

## Data Validation

Quality checks run automatically on fetched data:

```python
from src.pipeline.validator import DataValidator

validator = DataValidator()
report = validator.validate(data)

if not report.is_valid:
    for issue in report.issues:
        print(f"⚠️ {issue.severity}: {issue.description}")
```

### Checks Performed

| Check | Description |
|---|---|
| Missing values | Gaps in OHLCV data |
| Price anomalies | Sudden 50%+ moves (likely data errors) |
| Volume spikes | Unrealistic volume (possible data corruption) |
| Timestamp gaps | Missing trading days |
| OHLC consistency | High ≥ Open, Close, Low; Low ≤ Open, Close, High |
| Duplicate rows | Same timestamp appearing twice |

---

## Caching

SQLite-based cache avoids redundant API calls:

```python
from src.pipeline.cache import DataCache

cache = DataCache()

# Check cache
cached = cache.get("AAPL_1d_200")
if cached:
    return cached

# Fetch and store
data = exchange.get_ohlcv("AAPL", "1d", 200)
cache.set("AAPL_1d_200", data, ttl_seconds=3600)  # 1 hour TTL
```

### Cache Management

```bash
# CLI cache stats
python finclaw.py cache --stats

# Clear cache
python finclaw.py cache --clear
```

---

## Custom Data Transforms

Apply transforms to raw data before strategy consumption:

```python
import numpy as np

def add_returns(data):
    """Add daily return column."""
    prices = np.array([d["price"] for d in data])
    returns = np.diff(prices) / prices[:-1]
    for i, d in enumerate(data[1:], 1):
        d["return"] = float(returns[i - 1])
    return data

def add_log_returns(data):
    """Add log return column."""
    prices = np.array([d["price"] for d in data])
    log_returns = np.diff(np.log(prices))
    for i, d in enumerate(data[1:], 1):
        d["log_return"] = float(log_returns[i - 1])
    return data
```

---

## Pipeline Sinks

Export data to various destinations:

| Sink | Description |
|---|---|
| SQLite | Default local cache |
| CSV | `python finclaw.py export --ticker AAPL --format csv` |
| JSON | `python finclaw.py export --ticker AAPL --format json` |
| Webhook | Push data events to Slack/Discord/Teams |
