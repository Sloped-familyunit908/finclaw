# REST API Reference

FinClaw includes a built-in REST API server with authentication, rate limiting, and auto-generated Swagger docs. No Flask or FastAPI required — uses Python's built-in `http.server`.

---

## Starting the Server

```bash
python -m src.api.server --port 8080
```

- Swagger UI: `http://localhost:8080/api/v1/docs`
- OpenAPI spec: `http://localhost:8080/api/v1/openapi.json`

### With Authentication

```bash
export FINCLAW_API_KEY="your_secret_key"
python -m src.api.server --port 8080 --auth
```

Pass the key via header: `X-API-Key: your_secret_key`

---

## Endpoints

All endpoints are under `/api/v1`.

### Health Check

```bash
curl http://localhost:8080/api/v1/health
```

```json
{"status": "ok", "version": "5.2.0", "uptime_seconds": 42}
```

### List Exchanges

```bash
curl http://localhost:8080/api/v1/exchanges
```

```json
{
  "crypto": ["binance", "bybit", "okx", "coinbase", "kraken"],
  "stock_us": ["yahoo", "polygon", "alpha_vantage", "alpaca"],
  "stock_cn": ["akshare", "baostock", "tushare"]
}
```

### Get Quote

```bash
curl http://localhost:8080/api/v1/quote/yahoo/AAPL
```

```json
{
  "symbol": "AAPL",
  "last": 178.52,
  "bid": 178.50,
  "ask": 178.55,
  "volume": 52341000,
  "timestamp": "2026-03-16T15:30:00Z"
}
```

### Get OHLCV History

```bash
curl "http://localhost:8080/api/v1/history/yahoo/AAPL?timeframe=1d&limit=10"
```

```json
{
  "symbol": "AAPL",
  "exchange": "yahoo",
  "count": 10,
  "candles": [
    {"date": "2026-03-10", "open": 175.0, "high": 179.0, "low": 174.5, "close": 178.5, "volume": 50000000},
    ...
  ]
}
```

### List Strategies

```bash
curl http://localhost:8080/api/v1/strategies
```

### Run Backtest

```bash
curl -X POST http://localhost:8080/api/v1/backtest \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": "momentum",
    "tickers": "AAPL,MSFT",
    "start": "2023-01-01",
    "end": "2025-12-31",
    "capital": 100000
  }'
```

```json
{
  "strategy": "momentum",
  "annualized_return": 0.234,
  "sharpe_ratio": 1.45,
  "max_drawdown": -0.121,
  "win_rate": 0.58,
  "total_trades": 47,
  "profit_factor": 2.1
}
```

### Get Portfolio

```bash
curl http://localhost:8080/api/v1/portfolio
```

### Create Alert

```bash
curl -X POST http://localhost:8080/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT",
    "condition": "price_above",
    "threshold": 100000,
    "channel": "discord"
  }'
```

### List Alerts

```bash
curl http://localhost:8080/api/v1/alerts
```

---

## Authentication

When `--auth` is enabled, all endpoints except `/health`, `/docs`, and `/openapi.json` require an API key.

**Header method:**
```bash
curl -H "X-API-Key: your_key" http://localhost:8080/api/v1/quote/yahoo/AAPL
```

**Query parameter:**
```bash
curl "http://localhost:8080/api/v1/quote/yahoo/AAPL?api_key=your_key"
```

---

## Rate Limiting

The API includes built-in rate limiting. Default: 60 requests/minute per IP. Configurable via environment:

```bash
export FINCLAW_RATE_LIMIT=120  # requests per minute
```

---

## CORS

CORS is enabled by default for all origins. Configure in production:

```bash
export FINCLAW_CORS_ORIGIN="https://yourdomain.com"
```

---

## Webhooks

Push notifications to external services:

```bash
curl -X POST http://localhost:8080/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "condition": "rsi_below",
    "threshold": 30,
    "webhook": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
  }'
```

Supported channels: Slack, Discord, Microsoft Teams.
