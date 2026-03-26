# README Audit Report

**Date:** 2026-03-26
**README version analyzed:** Current HEAD
**pyproject.toml version:** 5.1.0

---

## Part 1 — Test Suite Results

```
Command: python -m pytest tests/ -q --tb=line (with PYTHONPATH=scripts;.)
Duration: 273.21s (4:33)
```

| Metric | Count |
|--------|-------|
| **Tests passed** | 5,590 |
| **Tests failed** | 1 |
| **Warnings** | 35 |
| **Collection errors** | 0 (after setting PYTHONPATH=scripts;.) |

### The 1 Failure

| Test | Category | Details |
|------|----------|---------|
| `test_coverage_expansion.py::TestConfigManager::test_default_config` | **Real bug** | `assert 0.005 == 0.001` — `get('backtest.commission')` returns 0.005 but test expects 0.001. The default commission value was changed but the test wasn't updated. |

### Notes on Running Tests
- Tests **cannot collect** without `PYTHONPATH=scripts;.` because `test_cli.py` and `test_exhaustive.py` import from `finclaw` (which lives at `scripts/finclaw.py`) and `test_mcp.py` imports from `mcp_server` (which lives at `scripts/mcp_server.py`).
- `pip install -e .` does NOT fix this — the package installs as `src.*`, not `finclaw`.
- Warnings are all expected: RuntimeWarning from divide-by-zero in edge cases, and a `dateutil` format warning in cache round-trip test.

---

## Part 2 — README vs Reality

### Numbers / Claims That Are WRONG or OUTDATED

| README Claim | Reality | Status |
|-------------|---------|--------|
| **"484 factors"** (title, badges, table, everywhere) | **41 hardcoded DNA weight dimensions** in `auto_evolve.py` (28 technical + 13 fundamental) + dynamic `custom_weights` from factor discovery. Even counting all possible dimensions generously (41 base + 15 cn_scanner + 9 Alpha158 KBAR), total is ~65 coded factors. The pyproject.toml description itself says "217 factors". **484 is not substantiated in the codebase.** | ❌ **Wrong** |
| **"33 categories"** (title, badges, table) | Factor discovery module defines **5 categories**: momentum, mean_reversion, volatility, technical, microstructure. The README table lists 18+ categories but many are aspirational or have inflated counts. | ❌ **Wrong** |
| **"Crypto-Specific: 200"** factors | `crypto_backtest.py` is a backtest execution engine (449 lines), not a factor library. `crypto_strategies.py` has 233 lines with no `compute_*` functions. There is no 200-factor crypto module. | ❌ **Wrong** |
| **"5000+ Tests"** (badge + Validation section) | **5,591 tests** (5,590 passed + 1 failed). Badge says "5000+" which is technically correct but could be updated to "5500+". | ⚠️ **Stale (undercount)** |
| **"280+ technical factors"** (Architecture diagram) | 28 technical weight keys in `_WEIGHT_KEYS`. Even counting individual indicator computations (RSI, MACD, BB, KDJ, etc.), it's ~20 compute functions. | ❌ **Wrong** |
| **"10 tools available"** (MCP section) | **10 tools** — ✅ Correct. `get_quote`, `get_history`, `list_exchanges`, `run_backtest`, `analyze_portfolio`, `get_indicators`, `screen_stocks`, `get_sentiment`, `compare_strategies`, `get_funding_rates`. | ✅ **Correct** |
| **"100+ Exchanges"** (badges, text) | Via ccxt, this is reasonable. ccxt supports 100+ exchanges. But FinClaw's own `src/exchanges/` has adapters for ~10 specific exchanges (Binance, OKX, Bybit, Coinbase, Kraken, Alpaca, Polygon, Alpha Vantage, Yahoo, AKShare, BaoStock, Tushare). The "100+" claim is a ccxt feature, not FinClaw-implemented. | ⚠️ **Misleading** |
| **pyproject.toml description says "217 factors"** | Disagrees with README's "484 factors". Neither number is accurate based on code analysis (~41–65 actual coded factors). | ❌ **Inconsistent** |
| **"Qlib Alpha158: 11"** factors in table | `alpha158_benchmark.py` computes **9 KBAR factors**. `alpha_factors.py` has 5 mathematical functions. Not 11. | ❌ **Wrong** |
| **"Davis Double Play: 8"** factors | There are fundamental factors in the DNA (revenue_yoy, PS, PEG, gross_margin, etc.) but they're mixed in "Fundamental" category. No separate "Davis Double Play" module with 8 factors exists. | ⚠️ **Unclear** |
| **"News Sentiment: 2"** factors | `src/sentiment/crypto_news.py` exists (4,353 bytes). Plausible but not wired into the 41 DNA weights. | ⚠️ **Partially true** |
| **"DRL Signals: 2"** factors | `src/drl/` has 1 .py file. Not wired into the 41 DNA weights. | ⚠️ **Partially true** |
| **Factor table totals** | The table explicitly says categories sum to "484 dimensions" with "33 categories". Based on code: 41 weights across ~8 logical categories. | ❌ **Wrong** |

### Claims That ARE Correct

| Claim | Status |
|-------|--------|
| MIT License | ✅ |
| Python 3.9+ | ✅ |
| MCP server with 10 tools | ✅ |
| Walk-forward validation | ✅ (in auto_evolve.py) |
| Arena mode | ✅ (src/evolution/arena.py exists) |
| Bias detection | ✅ (src/evolution/bias_cli.py exists) |
| Paper trading | ✅ (src/paper/ exists) |
| Dashboard exists | ✅ (dashboard/ directory) |
| Genetic algorithm evolution | ✅ (core of auto_evolve.py) |
| Multi-market (crypto + A-shares + US stocks) | ✅ |

---

## Part 3 — Quick Stats

### Codebase Size

| Metric | Count |
|--------|-------|
| Total .py files in src/ | 309 |
| Total lines in src/ | 72,067 |
| Total test files | 150 |
| Total test lines | 51,594 |
| Total code lines (src + tests) | ~123,661 |

### src/ Subdirectories (50 modules)

| Directory | .py files | Description |
|-----------|-----------|-------------|
| a2a/ | 3 | Agent-to-agent |
| agents/ | 3 | Backtester, stock picker, LLM analyzer |
| ai_strategy/ | 4 | AI strategy generation |
| alerts/ | 5 | Price alerts |
| analytics/ | 13 | Analytics modules |
| api/ | 5 | API layer |
| backtesting/ | 17 | Backtesting engine |
| cli/ | 8 | CLI commands |
| crypto/ | 9 | Crypto-specific modules |
| dashboard/ | 3 | Dashboard backend |
| data/ | 20 | Data fetching/caching |
| defi/ | 7 | DeFi protocols |
| deploy/ | 1 | Deployment scripts |
| derivatives/ | 3 | Derivatives |
| drl/ | 1 | Deep RL |
| events/ | 1 | Event system |
| evolution/ | 22 | Core evolution engine |
| exchanges/ | 22 | Exchange adapters |
| execution/ | 1 | Order execution |
| export/ | 1 | Data export |
| fixed_income/ | 1 | Fixed income |
| indicators/ | 3 | Alpha factors |
| journal/ | 1 | Trading journal |
| llm/ | 3 | LLM integration |
| mcp/ | 3 | MCP server |
| ml/ | 17 | ML pipeline |
| notifications/ | 8 | Notification system |
| optimization/ | 1 | Portfolio optimization |
| paper/ | 5 | Paper trading |
| paper_report/ | 1 | Paper trade reports |
| pipeline/ | 3 | Data pipeline |
| plugin_system/ | 7 | Plugin architecture |
| plugins/ | 9 | Built-in plugins |
| portfolio/ | 5 | Portfolio management |
| reporting/ | 3 | Report generation |
| reports/ | 8 | HTML reports |
| risk/ | 9 | Risk management |
| sandbox/ | 1 | Sandbox environment |
| screener/ | 4 | Stock screener |
| sentiment/ | 8 | Sentiment analysis |
| simulation/ | 1 | Market simulation |
| strategies/ | 34 | 15 top-level + 19 in library/ |
| strategy/ | 4 | Strategy framework |
| ta/ | 3 | Technical analysis |
| telegram_bot/ | 2 | Telegram integration |
| trading/ | 6 | Trading engine |
| utils/ | 1 | Utilities |
| viz/ | 3 | Visualization |
| watchlist/ | 1 | Watchlist management |

### Strategy Library

| Location | Count | Details |
|----------|-------|---------|
| src/strategies/ (top-level) | 15 files | ensemble, golden_dip, crypto_strategies, etc. |
| src/strategies/library/ | 19 files | bollinger, breakout, dca, grid_trading, etc. |
| strategies/builtin/ | 9 YAML files | Predefined strategy configs |
| scripts/finclaw.py STRATEGIES dict | 8 strategies | druckenmiller, soros, lynch, buffett, dalio, momentum, mean_reversion, aggressive |

### Factor Dimensions (Actual)

| Category | Count | Source |
|----------|-------|--------|
| Technical (core) | 11 | momentum, mean_reversion, volume, trend, pattern, MACD, Bollinger, KDJ, OBV, support, volume_profile |
| Technical (extended) | 10 | ATR, ADX, ROC, Williams %R, CCI, MFI, VWAP, Donchian, Ichimoku, Elder Ray |
| Rolling statistics | 7 | beta, R², residual, quantile_upper, quantile_lower, Aroon, price_volume_corr |
| Fundamental (original) | 4 | PE, PB, ROE, revenue_growth |
| Fundamental (growth) | 4 | revenue_yoy, revenue_qoq, profit_yoy, profit_qoq |
| Fundamental (valuation) | 2 | PS, PEG |
| Fundamental (quality) | 3 | gross_margin, debt_ratio, cashflow |
| **Total hardcoded** | **41** | In StrategyDNA class |
| cn_scanner signals (UnifiedDNA) | 15 | volume_breakout, bottom_reversal, macd_divergence, etc. |
| Alpha158 KBAR | 9 | KMID, KSFT, KLEN, etc. |
| Dynamic (factor discovery) | variable | LLM-generated, stored in custom_weights |
| **Total countable** | **~65** | Excluding dynamic discovery |

### Exchange Adapters

22 .py files in `src/exchanges/`, dedicated adapters for: Binance, Bybit, OKX, Coinbase, Kraken, Alpaca, Polygon, Alpha Vantage, Yahoo Finance, AKShare, BaoStock, Tushare, plus base/registry/aggregator/WS infrastructure.

---

## Summary of Recommended README Fixes

1. **Factor count**: Change "484 factors" → accurate number (41 core, ~65 total). Or if including all signal computations across all modules, do an honest count and explain methodology.
2. **Category count**: Change "33 categories" → ~8 actual categories (or however many are real).
3. **Crypto-Specific factor count**: "200" has no code backing. Remove or state actual number.
4. **Badge "factors-484"**: Update to match reality.
5. **Badge "categories-33"**: Update.
6. **Badge "tests-5000+"**: Can update to "tests-5500+" (5,591 actual).
7. **Architecture diagram "280+ factors"**: Fix.
8. **Factor Library table**: Audit each row's count against actual code.
9. **pyproject.toml description**: Align "217 factors" with README (both are wrong, but they should at least agree).
10. **Fix the 1 failing test**: `test_coverage_expansion.py::TestConfigManager::test_default_config` — update expected commission from 0.001 to 0.005.
