# Changelog

All notable changes to FinClaw are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Changed
- Consolidated 12 old benchmark scripts into `_scratch/benchmarks/`
- Expanded `.gitignore` with comprehensive Python, IDE, and OS patterns

## [0.10.0] - 2025-03

### Added
- PyPI package (`pip install finclaw-ai`)
- GitHub Actions CI/CD workflow for PyPI publishing
- Daily stock alert script — scans 50+ A-shares + HK, picks TOP 20

## [0.9.0] - 2025-03

### Added
- Expanded stock universe to 164 stocks (US 61, CN 84, HK 25)
- 9 cross-market sector linkages (optical, PCB, AI apps, commercial space)
- Telegram bot with formatted output (scan/backtest/macro/strategies)

## [0.8.0] - 2025-02

### Added
- MCP server with 4 tools (scan/backtest/macro/info) + 25 tests
- 5-market coverage: US, China, Hong Kong, Japan, Korea (77+ stocks)

### Changed
- Rebranded WhaleTrader → FinClaw
- License changed to AGPL-3.0 with commercial option

## [0.7.0] - 2025-02

### Added
- 6-layer deep macro analyzer (VIX, rates, DXY, oil, gold, copper, Kondratieff wave)
- Macro analysis integrated into CLI scan
- 102 exhaustive QA tests covering all strategy/market/ticker combos

## [0.6.0] - 2025-01

### Added
- v10 unified engine — 100万→354万 (5Y, 29.1% annual)
- LLM-enhanced stock picker with master strategy voting
- 5-year backtest across 80+ stocks (A-shares + US)

## [0.5.0] - 2025-01

### Added
- Multi-market benchmark (38 stocks, 5 markets) — wins 25/38 vs AHF
- Real data benchmark via yfinance — beats AHF 8/10
- Multi-language docs (中文, 日本語, 한국어, Français)
- TDD test suite (34 regression tests)

### Changed
- Bollinger Band confirmation factor (AHF-inspired) — +15.28% avg alpha

## [0.4.0] - 2024-12

### Added
- v7 momentum-adaptive engine (+12.54% avg alpha)
- Regime-based position scaling (7 regimes)
- Hot-hand / cold-hand position sizing

## [0.3.0] - 2024-12

### Added
- Statistical rigor overhaul
- 9 strategy templates (Druckenmiller, Soros, Buffett, etc.)
- Professional dashboard

## [0.2.0] - 2024-11

### Added
- AI integration + backtesting engine
- Agent memory system
- Constitutional risk management

## [0.1.0] - 2024-11

### Added
- Initial release as WhaleTrader
- AI-powered quantitative trading engine core
