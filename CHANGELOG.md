# Changelog

All notable changes to FinClaw are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/).

## [3.7.0] - 2026-03-16

### 📚 Documentation & Polish

- **Full API Reference** (`docs/api-reference.md`) — comprehensive docs for all strategies, TA indicators, ML models, risk tools, backtesting engine, CLI commands, and configuration
- **Tutorials** — 4 tutorial guides: quickstart, first-backtest, custom-strategy, risk-management
- **Architecture Document** (`docs/architecture.md`) — system architecture with Mermaid diagrams: module dependency graph, data flow, event system, plugin architecture
- **CHANGELOG** — complete changelog from v0.1 to v3.7
- Version bump to 3.7.0

## [3.6.0] - 2026-03-16

### Added
- **Event-Driven Backtester** (`src/backtesting/event_engine.py`) — full event-driven architecture with MarketEvent, SignalEvent, OrderEvent, FillEvent
- **Slippage Models v2** (`src/backtesting/slippage.py`) — configurable slippage models for event-driven backtester
- **Commission Models v2** (`src/backtesting/commission.py`) — tiered and flat commission models
- **Order Router** (`src/execution/order_router.py`) — smart order routing with venue selection
- 40+ new tests

## [3.5.0] - 2026-03-16

### Added
- **Market Data Router** (`src/data/data_router.py`) — automatic source selection and fallback
- **Webhook Notifier** (`src/notifications/webhook.py`) — Slack, Discord, Teams webhook integration
- **Tax Calculator** (`src/analytics/tax_calculator.py`) — tax lot tracking with FIFO/LIFO/specific ID
- **Benchmark Comparator** (`src/analytics/benchmark.py`) — enhanced benchmark comparison tools

## [3.4.0] - 2026-03-16

### Added
- **HTML Report Generator** enhancements — interactive equity curves, drawdown charts, trade table
- **PDF Reports** (`src/reports/pdf_report.py`) — export backtest results to PDF
- **Performance Report Card** (`src/reports/report_card.py`) — one-page strategy summary
- **Export Module** (`src/export/exporter.py`) — CSV, JSON, Parquet export

## [3.3.0] - 2026-03-16

### Added
- **Advanced Ensemble Model** (`src/ml/ensemble.py`) — stacking, blending, weighted average ensembles
- **Feature Store** (`src/ml/feature_store.py`) — centralized feature storage with versioning
- **News Sentiment ML** (`src/ml/news_sentiment.py`) — NLP-based news sentiment scoring
- **Regime Detector** (`src/ml/regime_detector.py`) — HMM-based market regime detection

## [3.2.0] - 2026-03-16

### Added
- **Advanced Risk Metrics** (`src/risk/advanced_metrics.py`) — Sharpe, Sortino, Calmar, Omega, tail ratio
- **Stress Tester** (`src/risk/stress_test.py`) — historical scenario stress tests (2008, COVID, rate hike)
- **Risk Budgeter** (`src/risk/risk_budget.py`) — risk parity allocation across strategies
- **VaR Calculator** enhancements — Monte Carlo VaR, Conditional VaR

## [3.1.0] - 2026-03-16

### Added
- **Sector Rotation** (`src/strategies/sector_rotation.py`) — relative momentum sector rotation
- **Drawdown Analyzer** (`src/analytics/drawdown.py`) — drawdown decomposition and recovery analysis
- **Trade Analyzer** (`src/analytics/trade_analyzer.py`) — per-trade P&L, win/loss streaks, trade duration
- **Signal Combiner** (`src/strategies/signal_combiner.py`) — weighted signal combination with confidence scoring
- 57 new tests

## [3.0.0] - 2026-03-16

### 🎉 Major Milestone — Platform Maturity Release

FinClaw v3.0 marks the transition from rapid feature development to a stable, production-ready quantitative finance platform.

### Highlights
- **777 tests** — comprehensive coverage across all 31 modules
- **Complete README overhaul** — architecture diagram, full feature matrix, competitor comparison
- **8 strategies** (6 equity + 3 crypto) with weighted ensemble combiner
- **17 technical indicators** — all pure NumPy, zero TA-Lib dependency
- **3 ML models** + alpha generation + Fama-French factor model
- **Options pricing** — Black-Scholes, Binomial Tree, Monte Carlo + Greeks + Vol Surface
- **Crypto/DeFi** — grid bot, DCA, arbitrage, on-chain analytics, yield tracking
- **Paper trading** — async simulated trading with risk checks and slippage modeling
- **Real-time streaming** — WebSocket market data with real-time TA
- **Walk-forward optimization** with overfitting detection and survivorship bias checks
- **Risk management** — VaR, Kelly criterion, position sizing, stop-loss, portfolio risk
- **Full CLI** + REST API + Interactive mode + Webhooks (Slack/Discord/Teams)
- **Realistic backtesting** — slippage, commissions, market impact, partial fills
- **Transaction cost analysis** — decomposition by commission, slippage, impact, opportunity cost

### Changed
- Version bumped to 3.0.0
- All `__init__.py` files reviewed and exports verified
- README completely rewritten for v3.0

## [2.4.0] - 2026-03-16

### Added
- **Paper Trading Engine** (`src/trading/paper_trader.py`): Async simulated live trading with risk checks, slippage modeling, position limits, and trade logging
- **Strategy Sandbox** (`src/sandbox/strategy_sandbox.py`): Safe execution environment for user-defined strategies with AST validation, forbidden construct blocking, and built-in backtesting
- **Portfolio Risk Dashboard** (`src/dashboard/risk_dashboard.py`): Real-time risk monitoring with VaR (95%/99%), HHI concentration, sector exposure, beta, drawdown, and HTML rendering
- **Fama-French Factor Model** (`src/ml/factor_model.py`): Multi-factor regression with OLS fitting, return prediction, factor attribution/decomposition, and t-statistics
- 37 new tests covering all v2.4.0 modules

## [2.3.0] - 2026-03-16

### Added
- **Realistic Backtest Engine** (`src/backtesting/realistic.py`) — Production-grade backtester with slippage models, commission models, market impact simulation, partial fills, market/limit/stop/stop-limit orders, and day-by-day portfolio tracking
- **Benchmark Suite** (`src/backtesting/benchmarks.py`) — Buy-and-hold, equal-weight, 60/40 classic portfolio, risk parity benchmarks with pre-built registry and `run_all_benchmarks()` convenience function
- **Strategy Comparator** (`src/backtesting/compare.py`) — Side-by-side comparison of multiple strategies with auto-ranking across 8 metrics (Return, CAGR, Sharpe, Sortino, MaxDD, Win Rate, PF, Calmar), correlation matrix, and formatted table output
- **Transaction Cost Analysis** (`src/analytics/tca.py`) — Full TCA decomposition: commissions, slippage, market impact, opportunity cost with breakdowns by ticker, hour, side, and trade size bucket
- **Enhanced HTML Reports** — Added TCA section and strategy comparison table to HTML backtest reports
- **46 new tests** covering all new modules: RealisticBacktester, SlippageModel, CommissionModel, MarketImpactModel, OrderBook, Benchmarks, StrategyComparator, TCA, HTML reports, and integration tests

### Changed
- Bumped backtesting `__init__.py` to v2.3.0 with all new exports
- Bumped analytics `__init__.py` to v2.3.0 with TCA exports
- HTML report generator now renders TCA and comparison sections when data provided

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
