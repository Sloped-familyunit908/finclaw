# Changelog

All notable changes to FinClaw are documented here.

## [5.2.0] — 2026-03-16

### Added
- **MCP Server** — Model Context Protocol integration for AI agents (Claude, Cursor, OpenClaw)
- Tools: `finclaw_scan`, `finclaw_backtest`, `finclaw_macro`, `finclaw_info`

## [5.1.0]

### Added
- REST API server with FastAPI — auth, rate limiting, OpenAPI docs

## [5.0.0]

### Added
- **Built-in Strategy Library** — 10 production-ready strategies in YAML
- Golden Cross Momentum, RSI Mean Reversion, MACD Divergence, Bollinger Squeeze, Grid Trading, DCA Smart, AI Sentiment Reversal, and more

## [4.9.0]

### Added
- Coinbase, Kraken, Alpaca, Polygon, Baostock exchange adapters (12 total)
- Exchange comparison CLI
- HTML backtest reports with equity curves and tearsheets

## [4.8.0]

### Added
- Data pipeline with SQLite caching and quality validation

## [4.6.0]

### Added
- DeFi & crypto extensions — DEX data, on-chain analytics, yield tracking

## [4.5.0]

### Added
- Advanced portfolio management — optimization, rebalancing, attribution

## [4.4.0]

### Added
- Notification hub — Telegram, email, webhook, smart alert engine

## [4.3.0]

### Added
- **Plugin system** — ABC-based plugin interfaces for strategies, indicators, exchanges
- Plugin manager with discover/load/unload/install lifecycle
- CLI plugin commands

## [4.2.0]

### Added
- Live trading engine with risk guard
- Paper trading sandbox
- Real-time dashboard

## [4.1.0]

### Added
- WebSocket real-time data — Binance, OKX, Bybit
- DataAggregator, MarketStore

## [4.0.0]

### Added
- Real exchange integration — 7 adapters with unified interface
- Exchange registry and CLI commands

## [3.8.0–3.9.0]

### Added
- ML Pipeline — feature engineering, model selection, prediction tracking
- CLI enhancements for risk, reporting, backtesting
- 1,100+ tests passing

## [3.5.0–3.7.0]

### Added
- Event-driven backtester with slippage/commission models
- Market data router, webhook notifier, tax calculator
- Documentation overhaul — API reference, tutorials, architecture

## [3.0.0–3.4.0]

### Added
- AI/ML enhancement — sentiment, regime detection, factor models
- Risk analytics — sector rotation, drawdown analyzer, signal combiner
- Reporting & visualization suite
- Major platform milestone — 777+ tests

## [2.0.0–2.9.0]

### Added
- Options & derivatives — Black-Scholes, binomial tree, Monte Carlo, Greeks
- Paper trading & strategy sandbox
- Interactive dashboard, PDF reports, trade journal
- Crypto & DeFi — grid bot, DCA, arbitrage, yield tracker, on-chain analytics
- Full CLI rewrite with interactive mode
- News sentiment pipeline, earnings calendar
- Config validation, type hints, error handling

## [1.0.0–1.9.0]

### Added
- Core engine — technical analysis (17 indicators), backtesting, screening
- ML integration — feature engineering, models, walk-forward validation
- Portfolio analytics — tracker, attribution, rebalancer
- Strategy combiner & optimizer
- HTML reports, SQLite cache, config system
- API layer and event-driven architecture
- Initial CI/CD pipeline
