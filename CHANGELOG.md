# Changelog

All notable changes to FinClaw are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/).

## [1.1.0] - 2026-03-16

### Added
- **66 new pytest tests** across 8 new test files covering signal engine, backtester, asset selector, stock picker, CLI, registry, universe, and macro modules
- Shared test fixtures in `tests/conftest.py` with synthetic price generators (bull, bear, crash, ranging, volatile)
- Expanded CI pipeline: Python 3.9–3.12 matrix, lint job (ruff), build verification job
- CONTRIBUTING.md rewritten with accurate project structure and workflow
- Comprehensive README with architecture diagram (Mermaid), API reference, feature comparison table, and quick start guide
- Cross-references to ClawGuard, AgentProbe, and repo2skill
- MANIFEST.in for proper sdist packaging
- `.npmignore`-equivalent exclusions via MANIFEST.in

### Changed
- CI workflow now tests Python 3.9+ (was 3.10+), adds lint and build jobs
- pyproject.toml version bumped to 1.1.0
- README restructured with architecture diagram, API docs, and comparison table

## [1.0.0] - 2026-03

### Added
- Stable release with 8 master strategies
- PyPI package (`pip install finclaw-ai`)
- MCP server with 4 tools
- Telegram bot interface
- Daily alert scanner

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
- 102 exhaustive QA tests covering all strategy/market/ticker combos

## [0.6.0] - 2025-01

### Added
- v10 unified engine — 100万→354万 (5Y, 29.1% annual)
- LLM-enhanced stock picker with master strategy voting

## [0.5.0] - 2025-01

### Added
- Multi-market benchmark (38 stocks, 5 markets) — wins 25/38 vs AHF
- Multi-language docs (中文, 日本語, 한국어, Français)
- TDD test suite (34 regression tests)

## [0.4.0] - 2024-12

### Added
- v7 momentum-adaptive engine (+12.54% avg alpha)
- Regime-based position scaling (7 regimes)

## [0.3.0] - 2024-12

### Added
- 9 strategy templates (Druckenmiller, Soros, Buffett, etc.)

## [0.2.0] - 2024-11

### Added
- AI integration + backtesting engine
- Agent memory system

## [0.1.0] - 2024-11

### Added
- Initial release as WhaleTrader
