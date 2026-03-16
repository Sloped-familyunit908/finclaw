# Changelog

All notable changes to FinClaw are documented here.

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
