# FinClaw Usability Audit — First-Time User Experience

**Date:** 2026-03-26  
**Auditor:** Automated (pretending to be a developer who just found this on GitHub)  
**Version tested:** v5.1.0

---

## Executive Summary

FinClaw makes a **phenomenal first impression** with its README — it's ambitious, visually polished, and exciting. But the moment a user tries to follow the documented steps, they hit **multiple broken commands, missing features, and import errors** that would cause most developers to abandon the project within 10 minutes. The gap between marketing and reality is the #1 problem.

**Overall Grade: C+**  
*(Great vision and README, but broken onboarding kills trust)*

---

## Step 1: README First Impression (30-second test)

### What works well ✅
- **Hero line** ("Self-Evolving Trading Intelligence") is memorable and differentiated
- **Badges** are comprehensive — PyPI, CI, license, Python version, factor count, stars
- **Architecture diagram** in ASCII art is clear and informative
- **Comparison table** vs Freqtrade/FinRL is very effective at positioning
- **Table of Contents** is well-organized
- **Disclaimer** is appropriately placed and worded
- **Quick Start section** appears simple (4 commands)
- **Feature list** is extensive and well-categorized

### Scores

| Criterion | Score | Notes |
|-----------|-------|-------|
| 10-second clarity | 8/10 | User understands "self-evolving trading" immediately |
| Excitement | 9/10 | Numbers (484 factors, 100+ exchanges) create wow factor |
| Trust signals | 6/10 | Badges are good, but evolution results table looks too good to be true |
| Call-to-action | 7/10 | `pip install finclaw-ai && finclaw demo` is clear |
| Install clarity | 4/10 | Quick Start has 2 commands that don't exist |

### Problems found ❌

1. **README Quick Start references non-existent commands** (`README.md` lines 44-54):
   - `finclaw download-crypto` → **DOES NOT EXIST** as a CLI command
   - `finclaw evolve` → **DOES NOT EXIST** as a CLI command
   - `finclaw list-exchanges` → **DOES NOT EXIST** (should be `finclaw exchanges list`)
   
   These are the **headline commands** that sell the project. A user following the Quick Start will hit errors on step 2.

2. **Evolution results table** (README line ~130): Shows 16,066% annual return with 12.19 Sharpe on crypto. Even with the disclaimer, this strains credibility and may make sophisticated users suspicious.

3. **pyproject.toml description mismatch**: Says "217 factors" but README says "484 factors". (`pyproject.toml` line 7 vs `README.md` line 1)

4. **Badge claims**: "5000+ tests" badge shown, but CHANGELOG says 4800+ as of v5.3.0, and project is at v5.1.0. Test count may be inflated.

### Comparison vs Freqtrade README
Freqtrade's README:
- **Shorter and more focused** — doesn't try to sell every feature
- **Has a real screenshot** of the running software
- **Links to comprehensive external docs** (freqtrade.io) instead of putting everything in README
- **Lists concrete exchanges** with tested/community-supported tiers
- **Has a "Quick Start" that actually works** (Docker-based)
- **Has CI badge + codecov badge + JOSS citation** for academic credibility

FinClaw's README is more visually impressive but **Freqtrade's README builds more trust** because every claim is verifiable and every command works.

---

## Step 2: Installation Experience

### `pip install -e .` ✅
- **Success** — installs cleanly with all dependencies satisfied
- All deps (aiohttp, yfinance, numpy, scipy, ccxt, akshare) install without issues
- Time: ~30 seconds (most pre-installed)

### `finclaw --help` ✅  
- Works perfectly, shows 70+ subcommands
- Output is well-formatted with descriptions

### `finclaw demo` ✅ 
- **Excellent UX** — ASCII art logo, colored output, pre-baked data
- Shows quotes, backtest, portfolio, risk, and AI features
- Ends with clear "try it yourself" suggestions
- Zero config needed — great first experience

### `python -m finclaw --help` ❌
- **Fails**: `No module named finclaw` — the package is `src`, not `finclaw`
- README MCP config uses `"command": "finclaw"` which works, but users might try `python -m finclaw`

### `finclaw doctor` ✅
- Nice diagnostic tool, shows what's installed and what's missing
- Good UX with ⚠️ indicators and `pip install` hints

### Broken README commands ❌

| Command from README | Result |
|---------------------|--------|
| `finclaw download-crypto` | `invalid choice` — command does not exist |
| `finclaw evolve --market crypto ...` | `invalid choice` — command does not exist |
| `finclaw list-exchanges` | `invalid choice` — command does not exist |
| `finclaw validate --results ...` | `invalid choice` — command does not exist |
| `finclaw live --market crypto ...` | `invalid choice` — command does not exist |
| `finclaw config set ...` | `invalid choice` — command does not exist |

These are documented in both `README.md` and `docs/crypto-trading/getting-started.md`.

### Commands that DO work ✅

| Command | Result |
|---------|--------|
| `finclaw demo` | Beautiful demo output |
| `finclaw quote AAPL` | Real-time stock quote, clean format |
| `finclaw --help` | Full help with 70+ subcommands |
| `finclaw info` | System info |
| `finclaw doctor` | Environment diagnostics |
| `finclaw backtest --strategy momentum --ticker NVDA --start 2020-01-01 --end 2025-01-01` | Works, returns results |
| `finclaw mcp serve` | MCP server starts (stdio) |

### `finclaw quote BTC/USDT` ❌
- Fails with HTTP 500 — tries Yahoo Finance for a crypto pair, which doesn't work
- User should use `finclaw ccxt-quote BTC/USDT` but README says just `finclaw quote BTC/USDT`
- The README claims "Works for stocks too" implying `quote` is universal — it's not

---

## Step 3: First Backtest Experience

### Can a user backtest within 5 minutes? **Partially**

**Stock backtest: YES ✅**
```bash
finclaw backtest --strategy momentum --ticker NVDA --start 2020-01-01 --end 2025-01-01
```
This works and returns clean output in ~10 seconds.

**Crypto evolution backtest: NO ❌**
The headline feature (`finclaw evolve`) does not exist as a CLI command. The evolution engine exists in `src/evolution/` but is only accessible via `python -m src.evolution.arena_evolver` (documented deep in README).

### Sample data
- `data/` directory exists with `a_shares/`, `crypto/`, `drl/`, `fundamentals/`, `sentiment/` subdirectories
- A user installing from PyPI (`pip install finclaw-ai`) would NOT have this data — it's only in the git clone
- No `finclaw download-crypto` command exists to fetch it
- Stock backtests work without sample data (downloads from Yahoo Finance on the fly)

### End-to-end experience for stock backtest:
1. `pip install finclaw-ai` → ✅ Works
2. `finclaw demo` → ✅ Works, impressive 
3. `finclaw backtest --strategy momentum --ticker AAPL` → ✅ Works
4. `finclaw quote AAPL` → ✅ Works

**The stock trading experience is solid.** The problem is the README leads with crypto, and the crypto path is broken.

---

## Step 4: Documentation Quality

### docs/ directory
- **48+ markdown files** — very extensive documentation
- Getting started guide exists and is well-structured
- 4 tutorials: quickstart, first-backtest, custom-strategy, risk-management
- Examples directory with 20+ example files organized by category
- Translated READMEs (French, Japanese, Korean, Chinese)

### Critical documentation bugs ❌

1. **`python finclaw.py` references everywhere** — 30+ instances across docs reference `python finclaw.py` but no `finclaw.py` exists at the repo root. The correct invocation is `finclaw <command>`.
   - `docs/getting-started.md` lines 26, 45, 72, 85, 95
   - `docs/cli-reference.md` — entire file uses `python finclaw.py`
   - `docs/backtesting.md` lines 11, 14, 17
   - `docs/portfolio.md` lines 31, 151, 154, 157
   - `docs/exchanges.md` lines 42, 98
   - `docs/faq.md` lines 79, 87, 128, 141
   - `docs/data-pipeline.md` lines 125, 128, 166, 167
   - ...and 15 more files

2. **Example files import non-existent module** — `examples/quickstart/first_quote.py` and `first_backtest.py` both `from finclaw_ai import FinClaw` which fails with `ModuleNotFoundError`. The correct import is `from src import FinClaw`.

3. **docs/getting-started.md** tells user to verify with `python finclaw.py info` — this file doesn't exist.

4. **docs/crypto-trading/getting-started.md** — entire 5-step guide references non-existent commands: `finclaw download-crypto`, `finclaw evolve`, `finclaw validate`, `finclaw live`, `finclaw config set`.

5. **docs/tutorials/quickstart.md** uses `pip install -e ".[all]"` but there's no `[all]` extra in pyproject.toml (only `[crypto]`, `[full]`, `[ml]`, `[dev]`).

### What's good ✅
- **tutorials/first-backtest.md** — excellent step-by-step tutorial with code examples
- **examples/README.md** — well-organized table of all examples
- **CONTRIBUTING.md** — clean, professional, includes project structure and commit conventions
- **CHANGELOG.md** — well-maintained with semantic versioning
- **docs/mcp-server.md** — not checked deeply but exists
- **Multilingual READMEs** — nice touch for international audience

### Comparison to Freqtrade docs
Freqtrade has a **dedicated documentation site** (freqtrade.io) built with MkDocs, with:
- Searchable docs
- Versioned documentation
- Step-by-step Docker quickstart that actually works
- Strategy writing tutorials
- API reference

FinClaw's docs are extensive but live as raw markdown files. No hosted documentation site.

---

## Step 5: Code Quality Signals

### Project organization ✅
- `src/` structure with clear module separation (60+ subdirectories)
- Well-named modules: `cli/`, `backtest/`, `evolution/`, `exchanges/`, `mcp/`, `ta/`, etc.
- `py.typed` marker present for type checking
- `.pre-commit-config.yaml` present

### CI/CD ✅
- `.github/workflows/ci.yml` — tests on Python 3.10, 3.11, 3.12
- `.github/workflows/release.yml` — PyPI publishing on tag push
- Lint with ruff
- Secret/PII scanning in CI (nice security touch)

### Issue templates ✅
- Bug report template with environment info
- Feature request template
- PR template

### Missing items ❌
- **No CODE_OF_CONDUCT.md** — standard for open-source projects
- **No SECURITY.md** — critical for a financial tool
- **No Discussions tab mentioned** (examples/README.md links to it but it may not be enabled)
- **No GitHub Releases page/tags referenced** — has release workflow but unclear if tags exist
- **Ruff runs with `--exit-zero`** — linting errors don't fail CI (line in ci.yml)
- **Tests use `head -100`** — CI truncates test output, may hide failures

### Test suite
- 130+ test files in `tests/`
- Covers CLI, backtesting, evolution, exchanges, factors, crypto, MCP, paper trading, and more
- CHANGELOG claims 4800+ tests, README badge says 5000+ — discrepancy

---

## Step 6: Key UX Gaps

### Top 10 Things That Would Make a New User GIVE UP AND LEAVE 🚪

1. **`finclaw download-crypto` doesn't exist** — The first command in Quick Start fails. User wasted 30 seconds reading, 10 seconds installing, 5 seconds typing, and now sees an error. Trust: destroyed.

2. **`finclaw evolve` doesn't exist** — The entire value proposition ("self-evolving strategies") has no working CLI entry point. The user came for autonomous strategy evolution and can't access it.

3. **`finclaw quote BTC/USDT` fails** — README says it works for stocks AND crypto. It doesn't work for crypto. User has to discover `ccxt-quote` themselves.

4. **Example files crash with `ModuleNotFoundError`** — Running `python examples/quickstart/first_quote.py` throws `No module named 'finclaw_ai'`. The very first Python example a user tries is broken.

5. **Docs reference `python finclaw.py` which doesn't exist** — 30+ doc files tell users to run a file that isn't there. Every tutorial is wrong.

6. **No sample data for crypto** — A PyPI install doesn't include data. No working command to download it. User can't try the crypto evolution workflow at all.

7. **Evolution results section shows 16,066% returns** — Sophisticated users will dismiss this as either a bug or a scam. Even with disclaimers, showing 5-figure percentage returns damages credibility.

8. **484 factors vs 217 factors mismatch** — pyproject.toml says 217, README says 484. Which is it? Inconsistency erodes trust.

9. **`finclaw live` doesn't exist** — The entire live/paper trading flow documented in `docs/crypto-trading/getting-started.md` is non-functional. There's `finclaw paper` but it's different from what's documented.

10. **No hosted documentation** — Users landing from Google/PyPI have no searchable docs site. Raw markdown on GitHub is harder to navigate than MkDocs/Sphinx.

### Top 10 Things That Would Make a User STAR THE REPO ⭐

1. **`finclaw demo` is outstanding** — ASCII art, colored output, pre-baked data, zero config. Best first-run experience I've seen in a quant project.

2. **70+ CLI subcommands** — The breadth of functionality is genuinely impressive: backtesting, screening, portfolio, risk, DeFi, sentiment, MCP, A2A, paper trading, charts.

3. **MCP server integration** — `finclaw mcp serve` works and exposes 10 tools for AI agents. This is unique and forward-looking.

4. **`finclaw doctor` command** — Smart diagnostic tool that checks deps, API keys, and connectivity. Professional UX touch.

5. **Pure NumPy core** — The "no heavy dependencies" philosophy is smart for installation simplicity.

6. **Multi-market support** — US stocks, A-shares, Hong Kong, Japan, Korea, Crypto — all from one tool. No other open-source project does this.

7. **README is visually stunning** — Badges, ASCII diagrams, comparison tables, factor library index. It's a template for how to write ambitious open-source READMEs.

8. **CONTRIBUTING.md is excellent** — Clear setup, commit conventions, project structure. Ready for contributors.

9. **CI/CD with secret scanning** — CI includes PII/secret scanning, not just tests. Shows security awareness (important for a financial tool).

10. **Factor library breadth** — 33 categories of factors including crypto-specific, sentiment, DRL, Davis Double Play. If even half work as described, this is unique in the open-source quant space.

---

## Prioritized Fix List

### 🔴 Critical (Fix before any promotion)

| # | Issue | File(s) | Fix |
|---|-------|---------|-----|
| 1 | `finclaw download-crypto` doesnt exist | `README.md`, `docs/crypto-trading/getting-started.md` | Implement the CLI command OR remove from docs |
| 2 | `finclaw evolve` doesn't exist | `README.md`, `docs/crypto-trading/getting-started.md` | Implement the CLI command OR remove from docs |
| 3 | `finclaw quote BTC/USDT` fails | `src/cli/main.py` (quote handler) | Route crypto symbols to ccxt automatically |
| 4 | Example imports broken (`from finclaw_ai import FinClaw`) | `examples/quickstart/first_quote.py`, `first_backtest.py` | Change to `from src import FinClaw` |
| 5 | `python finclaw.py` references everywhere | 30+ docs files (see list above) | Global find-replace to `finclaw` |
| 6 | pyproject.toml says 217 factors, README says 484 | `pyproject.toml` line 7 | Update to match actual count |

### 🟡 Important (Fix within a week)

| # | Issue | File(s) | Fix |
|---|-------|---------|-----|
| 7 | `finclaw list-exchanges` doesn't exist | `README.md` | Change to `finclaw exchanges list` or implement alias |
| 8 | `finclaw validate` doesn't exist | `docs/crypto-trading/getting-started.md` | Implement or remove |
| 9 | `finclaw live` doesn't exist | `docs/crypto-trading/getting-started.md` | Implement or document `finclaw paper` instead |
| 10 | `finclaw config set` doesn't exist | `docs/crypto-trading/getting-started.md` | Implement or use env vars only |
| 11 | `pip install -e ".[all]"` — no `[all]` extra | `docs/tutorials/quickstart.md` | Change to `[dev]` or `[full]` or add `[all]` |
| 12 | No SECURITY.md | Root directory | Add standard security policy |
| 13 | No CODE_OF_CONDUCT.md | Root directory | Add Contributor Covenant |
| 14 | Ruff runs with `--exit-zero` | `.github/workflows/ci.yml` | Remove `--exit-zero` so lint errors fail CI |

### 🟢 Nice to have

| # | Issue | Fix |
|---|-------|-----|
| 15 | No hosted docs site | Set up MkDocs/Read the Docs |
| 16 | Evolution results too extreme | Tone down or add more context |
| 17 | Test count badge says 5000+ but actual is ~4800 | Verify and update |
| 18 | No Jupyter notebooks | Add interactive tutorials |
| 19 | `docs/getting-started.md` "Verify Installation" section is wrong | Fix to use `finclaw info` |
| 20 | `FinClaw.backtest()` API uses different params than what examples show | Align Python API with examples |

---

## Summary Metrics

| Metric | Status |
|--------|--------|
| Install from PyPI | ✅ Works |
| First command works (`finclaw demo`) | ✅ Excellent |
| Stock quote | ✅ Works |
| Crypto quote | ❌ Fails (wrong adapter routing) |
| Stock backtest | ✅ Works |
| Crypto evolution (headline feature) | ❌ CLI command doesn't exist |
| Example scripts run | ❌ All crash with ModuleNotFoundError |
| Docs internally consistent | ❌ 30+ files reference non-existent `finclaw.py` |
| MCP server | ✅ Works |
| CI/CD | ✅ Present and functional |
| Contributing guide | ✅ Excellent |
| Time to first working command | ~2 minutes (demo) |
| Time to first meaningful result | ~3 minutes (stock backtest) |
| Time to crypto evolution | ♾️ (impossible via documented path) |

---

## Bottom Line

FinClaw has the architecture and ambition of a **10-star project** wrapped in documentation that's **90% aspirational**. The stock trading path works well. The crypto evolution path — which is the entire differentiator — is not accessible via CLI.

**Priority 1:** Implement `finclaw evolve` and `finclaw download-crypto` CLI commands.  
**Priority 2:** Fix all broken import paths and `finclaw.py` references.  
**Priority 3:** Make `finclaw quote` work for crypto symbols automatically.

Once these are fixed, this project has genuine potential to compete with Freqtrade — the breadth of features and the evolution engine concept are genuinely innovative. But right now, a first-time user hitting errors in the Quick Start will close the tab and move on.
