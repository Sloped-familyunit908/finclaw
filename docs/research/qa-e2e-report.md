# FinClaw v5.1.0 — End-to-End QA Report

**Date:** 2026-03-27  
**Tester:** QA Subagent (Chief QA Engineer)  
**Environment:** Windows 10 (x64), Python 3.12, finclaw-ai 5.1.0 (editable install)

---

## Phase 1: Installation & First Run

| # | Test | Result | Notes |
|---|------|--------|-------|
| 1.1 | `pip install -e .` | ✅ PASS | Clean install, all deps satisfied, built editable wheel |
| 1.2 | `finclaw --version` | ✅ PASS | `finclaw 5.1.0` |
| 1.3 | `finclaw demo` | ✅ PASS | Beautiful ASCII banner, pre-baked data, all sections render correctly. No errors. |
| 1.4 | `finclaw doctor` | ✅ PASS | 13 passed, 13 warnings (all optional deps/API keys). Clear remediation hints. |

---

## Phase 2: Quote & Data Commands

| # | Test | Result | Notes |
|---|------|--------|-------|
| 2.1 | `finclaw quote AAPL` | ✅ PASS | `AAPL $252.89 +3.93 +1.58%` — price verified against direct yfinance |
| 2.2 | `finclaw quote MSFT GOOGL` | ✅ PASS | Multi-quote table rendered correctly |
| 2.3 | `finclaw quote BTC/USDT` | ✅ PASS | `BTC/USDT $68490.00 -2.05%` with bid/ask/vol |
| 2.4 | `finclaw quote ETH/USDT` | ✅ PASS | `ETH/USDT $2063.71 -2.55%` |
| 2.5 | `finclaw ccxt-quote BTC/USDT` | ⚠️ WARN | Binance returns HTTP 451 (geo-restricted). Error message is clear but no fallback exchange attempted. |
| 2.6 | `finclaw history AAPL -l 5` | ✅ PASS | 5 candles, correct OHLCV format |
| 2.7 | `finclaw cn-realtime 600519` | ❌ FAIL | Positional arg not accepted: `error: unrecognized arguments: 600519`. Must use `--code 600519`. |
| 2.8 | `finclaw exchanges list` | ✅ PASS | Lists crypto, stock_us, stock_cn exchanges |
| 2.9 | `finclaw info` | ⚠️ WARN | Shows only 12 commands of 60+. Incomplete command list. |
| 2.10 | `finclaw fear-greed` | ✅ PASS | `13/100 — Extreme Fear` with progress bar |
| 2.11 | `finclaw funding-rates` | ✅ PASS | Multi-exchange dashboard with arbitrage opportunities |
| 2.12 | `finclaw gainers` | ⚠️ WARN | Data correct but **raw ANSI escape codes leak** in output: `[92m +2.02%[0m` |
| 2.13 | `finclaw losers` | ⚠️ WARN | Same ANSI escape code leakage: `[91m -7.96%[0m` |

---

## Phase 3: Analysis & Backtest Commands

| # | Test | Result | Notes |
|---|------|--------|-------|
| 3.1 | `finclaw analyze --ticker AAPL` | ✅ PASS | RSI, MACD, Bollinger all rendered |
| 3.2 | `finclaw backtest --strategy momentum --ticker AAPL` | ✅ PASS | +27.1% return, 18 trades, 50% win rate. Plausible. |
| 3.3 | `finclaw backtest --strategy mean_reversion --ticker MSFT` | ⚠️ WARN | Falls through to default (v7) strategy with WARNING. The result header says `MSFT | mean_reversion` but it's not actually mean_reversion. Misleading. |
| 3.4 | `finclaw compare --strategies momentum,mean_reversion --tickers AAPL` | ❌ FAIL | `--tickers` not recognized. Must use `--data AAPL`. CLI flag inconsistency between `backtest` and `compare`. |
| 3.4b | `finclaw compare --strategies momentum mean_reversion --data AAPL` | ✅ PASS | Works with correct flags |
| 3.5 | `finclaw scan-cn` | ✅ PASS | 30 stocks scanned, correct Chinese names, buy signals with scores |
| 3.6 | `finclaw screen --criteria "rsi<30"` | ⚠️ WARN | `No screening criteria specified` — the `--criteria` flag is accepted but apparently not parsed. Had to use `--rsi-below 30`. |
| 3.7 | `finclaw sentiment TSLA` | ✅ PASS | Sentiment score, headline count, Fear & Greed breakdown |
| 3.8 | `finclaw news AAPL` | ✅ PASS | 10 headlines from cnbc, marketwatch, yahoo_finance. Truncated text but readable. |
| 3.9 | `finclaw trending` | ✅ PASS | Topic mentions + WSB section (empty due to Reddit unavailability — handled gracefully) |
| 3.10 | `finclaw regime --symbol AAPL` | ✅ PASS | STABLE regime, adaptive strategy weights shown. Requires `--symbol` (not positional). |

---

## Phase 4: Evolution & Crypto Commands

| # | Test | Result | Notes |
|---|------|--------|-------|
| 4.1 | `finclaw evolve --help` | ✅ PASS | Clear options: generations, population, mutation rate, etc. |
| 4.2 | `finclaw download-crypto --help` | ✅ PASS | Supports --coins and --days |
| 4.3 | `finclaw check-backtest` | ⚠️ WARN | With no args, shows all zeros and says "✅ All checks passed". Misleading — should warn that no data was provided. |

---

## Phase 5: Paper Trading & Portfolio

| # | Test | Result | Notes |
|---|------|--------|-------|
| 5.1 | `finclaw paper --help` | ✅ PASS | Full subcommand tree: start, buy, sell, portfolio, pnl, history, dashboard, run-strategy, journal, reset |
| 5.2 | `finclaw portfolio --help` | ✅ PASS | track, add, remove, show, history, alert, export |
| 5.3 | `finclaw risk --help` | ✅ PASS | Requires --portfolio JSON file |
| 5.4 | `finclaw watchlist --help` | ✅ PASS | create, quotes, add, remove, export, list |

---

## Phase 6: AI & MCP Features

| # | Test | Result | Notes |
|---|------|--------|-------|
| 6.1 | `finclaw mcp --help` | ✅ PASS | serve + config subcommands |
| 6.2 | `finclaw generate-strategy --help` | ✅ PASS | Natural language input, market selection, risk profile, LLM provider config |
| 6.3 | `finclaw copilot --help` | ✅ PASS | Minimal help (no args needed) |
| 6.4 | `finclaw a2a --help` | ✅ PASS | serve + card subcommands |

---

## Phase 7: Edge Cases & Error Handling

| # | Test | Result | Notes |
|---|------|--------|-------|
| 7.1 | `finclaw quote INVALIDTICKER` | ✅ PASS | Clear error: `HTTP 404 — No data found, symbol may be delisted`. Exit code 1. |
| 7.2 | `finclaw backtest --strategy nonexistent --ticker AAPL` | ⚠️ WARN | Shows WARNING but silently falls back to default strategy. Output header says `AAPL | nonexistent` which is misleading. Should either fail or clearly label output as `default/v7`. |
| 7.3 | `finclaw quote` (no ticker) | ✅ PASS | Clear argparse error with usage hint |
| 7.4 | `finclaw analyze` (no ticker) | ✅ PASS | Clear argparse error: `--ticker/-t required` |

---

## Phase 8: Data Accuracy Spot Check

| # | Test | Result | Notes |
|---|------|--------|-------|
| 8.1 | AAPL price accuracy | ✅ PASS | finclaw: $252.89, direct yfinance: $252.89 — exact match |
| 8.2 | Momentum backtest plausibility | ✅ PASS | +27.1% over 5yr (AAPL B&H was +113.9%). Alpha is negative which is realistic for a simple momentum strategy. |
| 8.3 | scan-cn stock code mapping | ✅ PASS | 601318=中国平安, 600030=中信证券, 688111=金山办公 — all correct |

---

## Additional Tests

| # | Test | Result | Notes |
|---|------|--------|-------|
| A.1 | `finclaw chart AAPL` | ✅ PASS | Beautiful Braille-character terminal chart, 6mo default |
| A.2 | `finclaw market-check` | ✅ PASS | Shanghai index regime detection (BEAR, score 25.3) |
| A.3 | `finclaw strategy list` | ✅ PASS | 15 built-in + 6 YAML DSL strategies listed with descriptions |
| A.4 | `finclaw predict run --symbol AAPL` | ⚠️ WARN | Shows "Prediction engine ready" but no actual prediction output. Feels like a stub. |
| A.5 | `finclaw info AAPL` | ✅ PASS | Shows price, change, 52w range, volatility |
| A.6 | `finclaw cn-realtime -c 600519` | ✅ PASS | "No data returned. Market may be closed" — correct for after-hours |
| A.7 | `finclaw regime` (no args) | ✅ PASS | Clear argparse error: `--symbol/-s required` |

---

## Summary

| Category | Passed | Failed | Warnings |
|----------|--------|--------|----------|
| Phase 1: Installation | 4 | 0 | 0 |
| Phase 2: Quotes & Data | 7 | 1 | 4 |
| Phase 3: Analysis & Backtest | 7 | 1 | 2 |
| Phase 4: Evolution & Crypto | 2 | 0 | 1 |
| Phase 5: Paper & Portfolio | 4 | 0 | 0 |
| Phase 6: AI & MCP | 4 | 0 | 0 |
| Phase 7: Edge Cases | 3 | 0 | 1 |
| Phase 8: Data Accuracy | 3 | 0 | 0 |
| Additional | 6 | 0 | 1 |
| **TOTAL** | **40** | **2** | **9** |

---

## Priority-Ordered Bug List

### 🔴 P0 — Must Fix

1. **`cn-realtime` rejects positional stock code** — `finclaw cn-realtime 600519` fails with `unrecognized arguments`. User must know to use `--code 600519`. The README/docs likely show the positional form. Fix: add positional argument support or update docs.

2. **`compare` uses `--data` but `backtest` uses `--ticker/--tickers`** — `finclaw compare --strategies momentum,mean_reversion --tickers AAPL` fails. Inconsistent CLI flags between related commands confuse users.

### 🟡 P1 — Should Fix

3. **ANSI escape code leakage in `gainers`/`losers`** — Raw `[92m` and `[91m` codes appear in output on Windows CMD. Colors render correctly in terminals that support ANSI but leak in others. Need to detect terminal capability or use colorama `init()`.

4. **`backtest --strategy nonexistent` misleading output** — Falls back to default (v7) but labels output as `nonexistent`. Should either error out or label as `default/v7` in the output header.

5. **`check-backtest` with no args passes all checks** — Shows 0 trades, 0% return, Sharpe 0.00 and says "✅ All checks passed". Should require at least --input or show a warning that no data was analyzed.

6. **`screen --criteria "rsi<30"` silently ignored** — The `--criteria` flag exists in argparse but doesn't trigger filtering. Only dedicated flags like `--rsi-below 30` work. Either implement the criteria parser or remove the flag.

### 🟢 P2 — Nice to Have

7. **`info` command shows incomplete command list** — Only lists 12 of 60+ commands. Should show all commands or link to `--help`.

8. **`ccxt-quote` no fallback exchange** — When Binance is geo-restricted (HTTP 451), no alternative exchange is tried. Could auto-fallback to bybit/okx.

9. **`predict run` appears to be a stub** — Shows "Prediction engine ready" but doesn't actually output a prediction. Should either produce a result or clearly state it needs configuration.

10. **`regime` requires `--symbol` flag** — Would be more natural as a positional argument: `finclaw regime AAPL`.

---

## Recommended Unit Test Additions

### Critical (should exist but don't)

1. **`test_cn_realtime_positional_arg`** — Verify `cn-realtime 600519` works the same as `cn-realtime --code 600519`
2. **`test_compare_ticker_flag_consistency`** — Verify `compare --tickers` works (or test that error message is helpful)
3. **`test_backtest_unknown_strategy_output_label`** — When using unknown strategy, verify output doesn't label results as the unknown strategy name
4. **`test_screen_criteria_string_parsing`** — Verify `--criteria "rsi<30"` actually filters results
5. **`test_check_backtest_no_input_warning`** — Verify that running check-backtest with no data produces a warning, not a green "all passed"

### Important

6. **`test_gainers_losers_no_raw_ansi`** — Verify output doesn't contain raw ANSI escape sequences
7. **`test_quote_invalid_ticker_graceful`** — Verify invalid tickers produce clean error (already passes, should be codified)
8. **`test_quote_no_args_usage`** — Verify no-argument invocation shows usage (already passes)
9. **`test_ccxt_quote_geo_restricted_fallback`** — Test behavior when primary exchange is unavailable
10. **`test_predict_run_produces_output`** — Verify prediction actually returns a value, not just "ready"

### Nice to Have

11. **`test_info_lists_all_commands`** — Verify `info` output includes all registered commands
12. **`test_regime_positional_symbol`** — Test `finclaw regime AAPL` acceptance
13. **`test_demo_no_errors`** — Run demo and assert exit code 0, no tracebacks
14. **`test_funding_rates_arbitrage_math`** — Verify arbitrage spread calculation is correct
15. **`test_scan_cn_stock_name_mapping`** — Verify known codes map to correct company names

---

## Overall Quality Score

### **B+**

**Strengths:**
- Installation is smooth, zero-config demo is excellent
- Core features (quote, backtest, analyze, scan-cn) work reliably
- Data accuracy is spot-on (verified against direct API)
- Error messages for invalid tickers are clear and helpful
- Feature breadth is impressive: 60+ commands covering stocks, crypto, A-shares, paper trading, AI
- Terminal charts and ASCII art are polished
- Doctor command gives actionable remediation hints

**Weaknesses:**
- CLI flag inconsistency between related commands (`--ticker` vs `--data` vs `--tickers`)
- ANSI color leakage on Windows for gainers/losers
- Some features appear to be stubs (`predict run`)
- `--criteria` flag on `screen` is essentially non-functional
- `check-backtest` gives false confidence with no data
- Minor positional-vs-flag UX inconsistencies

**Bottom Line:** The product is solid for a v5.1 release. Core value proposition (quotes, analysis, backtesting, A-share scanning) works well. The main issues are CLI consistency and a few half-implemented features. Nothing is a showstopper but the P0/P1 bugs would confuse a new user who clones from GitHub.
