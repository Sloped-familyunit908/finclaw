# Changelog

All notable changes to FinClaw are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/).

## [2.0.0] - 2026-03-16

### Added
- **Configuration Validation** - validates `finclaw.yml` on load with required fields, type checking, and range validation (e.g., commission must be 0–1)
- **Type Hints Audit** - added comprehensive type annotations to all public APIs in `src/strategies/`, `src/backtesting/`, `src/risk/`, and `src/ml/`
- **Error Handling** - user-friendly error messages across CLI commands, data fetching, strategy execution, and backtest runner with graceful degradation
- **Missing `__init__.py` files** - ensured all packages have proper `__init__.py` with clean imports
- **CLI entry point** - `finclaw` command via `project.scripts` in pyproject.toml

### Changed
- **Version bumped to 2.0.0** - major milestone release
- **pyproject.toml** - added all dependencies (numpy, pyyaml), proper classifiers, entry points
- **Config loader** - now raises `ConfigValidationError` on invalid config instead of silently falling back to defaults
- **CLI** - all commands now catch exceptions and print user-friendly error messages instead of tracebacks

### Fixed
- Clean imports across all modules

## [1.9.0] - 2026-03-16

### Added
- Comprehensive README with architecture diagram, API reference, examples
- Integration tests for full pipeline coverage
- API documentation for all public modules

## [1.8.0] - 2026-03-16

### Added
- **REST API layer** (`src/api/server.py`) - HTTP endpoints for scan, backtest, signal
- **Webhook support** (`src/api/webhooks.py`) - push notifications for signals and alerts
- Integration tests for API endpoints

## [1.7.0] - 2026-03-16

### Added
- **Event-driven architecture** (`src/events/event_bus.py`) - pub/sub event system for strategy signals, trade executions, and alerts
- **Advanced analytics** - rolling metrics, regime detection, correlation analysis, execution analytics

## [1.6.0] - 2026-03-16

### Added
- **Portfolio tracker** (`src/portfolio/tracker.py`) - real-time portfolio value tracking
- **Technical indicators** (`src/ta/indicators.py`) - RSI, MACD, Bollinger Bands, ATR, Stochastic
- **Stock screener** (`src/screener/stock_screener.py`) - filter stocks by technical/fundamental criteria
- **Alert engine** (`src/alerts/alert_engine.py`) - price and signal-based alerts
- **Attribution analysis** (`src/analytics/attribution.py`) - Brinson-style performance attribution
- 38 new tests

## [1.5.0] - 2026-03-16

### Added
- **ML Integration** - feature engineering, numpy-only ML models, sentiment analysis, alpha model, walk-forward pipeline
- `src/ml/features.py` - FeatureEngine with 20+ technical features
- `src/ml/models.py` - LinearRegression, MAPredictor, RegimeClassifier, EnsembleModel
- `src/ml/sentiment.py` - keyword-based sentiment analyzer
- `src/ml/alpha.py` - multi-signal alpha model with IC tracking
- `src/ml/pipeline.py` - walk-forward ML pipeline
- 56 new tests

## [1.4.0] - 2026-03-16

### Added
- **Enhanced CLI** - scan, backtest, signal, optimize, report, portfolio, cache commands
- **HTML Reports** (`src/reports/html_report.py`) - interactive backtest reports
- **Config System** (`src/config.py`) - YAML-based configuration with `finclaw.yml`
- **SQLite Cache** (`src/pipeline/cache.py`) - persistent data cache with TTL
- 38 new tests

## [1.3.0] - 2026-03-16

### Added
- **Strategy Combiner** (`src/strategies/combiner.py`) - combine multiple strategies with configurable weights, confidence scoring, and regime detection
- **Strategy Optimizer** (`src/optimization/optimizer.py`) - grid search and random search over strategy parameters
- **Signal Dashboard** (`src/dashboard/signals.py`) - signal reports with risk metrics
- **Backtest Report Generator** (`src/reports/backtest_report.py`) - full backtest reports
- **Portfolio Rebalancer** (`src/portfolio/rebalancer.py`) - calendar, threshold, and tax-aware rebalancing
- 42 new tests

## [1.2.0] - 2026-03-16

### Added
- Enhanced backtesting engine with walk-forward analysis, Monte Carlo simulation
- Multi-timeframe backtesting (daily, weekly, monthly)
- Benchmark comparison (SPY/QQQ)
- Risk management: Kelly criterion, position sizing, stop-loss manager, VaR calculator
- Portfolio-level risk management

## [1.1.0] - 2026-03-16

### Added
- 66 new pytest tests across 8 test files
- Python 3.9-3.12 CI matrix, lint, build verification
- CONTRIBUTING.md, comprehensive README

## [1.0.0] - 2026-03

### Added
- Stable release with 8 master strategies
- PyPI package (`pip install finclaw-ai`)
- MCP server with 4 tools
- Telegram bot interface
- Daily alert scanner

## [0.10.0] - 2025-03

### Added
- PyPI package, GitHub Actions CI/CD
- Daily stock alert script

## [0.9.0] - 2025-03

### Added
- Expanded stock universe to 164 stocks (US 61, CN 84, HK 25)
- 9 cross-market sector linkages
- Telegram bot

## [0.8.0] - 2025-02

### Added
- MCP server with 4 tools
- 5-market coverage (77+ stocks)

### Changed
- Rebranded WhaleTrader → FinClaw
- License changed to AGPL-3.0

## [0.7.0] - 2025-02

### Added
- Deep macro analyzer (VIX, rates, DXY, oil, gold, copper)
- 102 exhaustive QA tests

## [0.6.0] - 2025-01

### Added
- v10 unified engine
- LLM-enhanced stock picker

## [0.5.0] - 2025-01

### Added
- Multi-market benchmark (38 stocks, 5 markets)
- Multi-language docs

## [0.4.0] - 2024-12

### Added
- v7 momentum-adaptive engine
- Regime-based position scaling

## [0.3.0] - 2024-12

### Added
- 9 strategy templates

## [0.2.0] - 2024-11

### Added
- AI integration + backtesting engine
- Agent memory system

## [0.1.0] - 2024-11

### Added
- Initial release as WhaleTrader
