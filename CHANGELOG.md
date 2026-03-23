# Changelog

All notable changes to this project will be documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [5.2.0] - 2026-03-23

### Added
- Factor Quality Analysis: IC/IR/decay/tier classification for all 217 factors
- Factor Correlation Matrix: NxN orthogonality detection with auto-pruning
- 21 new factors: 10 alternative data + 11 Qlib Alpha158 gap-fill
- Monte Carlo validation for strategy robustness
- Turnover penalty in fitness function
- best_ever.json: persistent all-time best strategy DNA
- Hall of Fame: timestamped copies of every record-breaking DNA
- 291 new tests (total: 4753+)
- Factor gap analysis vs Qlib Alpha158 (docs/factor_gap_analysis.md)
- Code coverage with pytest-cov (.coveragerc + CI integration)

### Fixed
- Limit-down exit bug in backtest engine
- 10 stale test references to removed modules
- Killed stale download_a_shares.py process

## [5.1.0] - 2026-03-21

### Added
- Real-time dashboard with live market data (US, CN, Crypto)
- Stock detail pages with TradingView charts and technical indicators
- Strategy evolution engine with genetic algorithm optimization
- Walk-forward validation and Monte Carlo simulation
- Multi-agent debate system for consensus-based analysis
- A2A (Agent-to-Agent) protocol support
- MCP server for AI agent integration

### Changed
- Dashboard redesigned with professional UI (no emoji, data-dense layout)
- All market data now fetched from real APIs (Yahoo Finance, Sina, CoinGecko)
- README cleaned up for professional open-source presentation

### Fixed
- Exchange adapters now handle network errors with retry and rate limiting
- Flaky timestamp test in snapshot manager
- SMA values on homepage cards were showing stale mock data

## [0.1.0] - 2026-03-17

Initial release.

### Features
- **FinClaw API** - High-level `FinClaw` class with `quote()`, `backtest()`, and `paper_trade()` methods
- **Yahoo Finance adapter** - Real-time quotes via yfinance, no API key needed
- **Backtesting engine** - Event-driven backtester with slippage/commission models
- **Paper trading** - Simulated live trading with built-in strategy runners
- **MCP Server** - Model Context Protocol integration for AI agents (Claude, Cursor, OpenClaw)
- **CLI** - Command-line interface for quotes, backtesting, and scanning
- **WebSocket streaming** - Real-time data from Binance, OKX, Bybit
- **Strategy library** - YAML-configured strategies (momentum, mean-reversion, grid, DCA)
- **HTML reports** - Backtest tearsheets with equity curves and drawdown analysis
- **Plugin system** - Extensible architecture for custom strategies and exchange adapters
