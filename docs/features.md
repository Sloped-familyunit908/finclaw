# FinClaw — Feature Reference

## Factor Library (484 factors)

284 general factors + 200 crypto-specific factors, organized across categories:

| Category | Count | Examples |
|----------|-------|---------|
| Crypto-Specific | 200 | Funding rate proxy, session effects, whale detection, liquidation cascade |
| Momentum | 14 | ROC, acceleration, trend strength, quality momentum |
| Volume & Flow | 13 | OBV, smart money, volume-price divergence, Wyckoff VSA |
| Volatility | 13 | ATR, Bollinger squeeze, regime detection, vol-of-vol |
| Mean Reversion | 12 | Z-score, rubber band, Keltner position |
| Trend Following | 14 | ADX, EMA golden cross, higher-highs-lows, MA fan |
| Qlib Alpha158 | 11 | KMID, KSFT, CNTD, CORD, SUMP (Microsoft Qlib compatible) |
| Quality Filter | 11 | Earnings momentum proxy, relative strength, resilience |
| Risk Warning | 11 | Consecutive losses, death cross, gap-down, limit-down |
| Top Escape | 10 | Distribution detection, climax volume, smart money exit |
| Price Structure | 10 | Candlestick patterns, support/resistance, pivot points |
| Davis Double Play | 8 | Revenue acceleration, tech moat, supply exhaustion |
| Alpha | 10 | Various alpha factor implementations |
| Gap Analysis | 8 | Gap fill, gap momentum, gap reversal |
| Market Breadth | 5 | Advance-decline, sector rotation, new highs/lows |
| News Sentiment | 2 | EN/ZH keyword sentiment score + momentum |
| DRL Signals | 2 | Q-learning buy probability + state value estimate |
| ... and more | 130 | Fundamental proxy, pullback, bottom confirmation, regime, etc. |

> **Design principle**: Every signal — technical, sentiment, DRL, fundamental — is expressed as a factor returning `[0, 1]`. The evolution engine decides the weight. No human bias in signal mixing.

---

## Evolution Engine

The genetic algorithm continuously discovers optimal strategies:

1. **Seed** — Initialize population with diverse factor weight configurations
2. **Evaluate** — Backtest each DNA with walk-forward validation
3. **Select** — Keep the top performers
4. **Mutate** — Random weight perturbations, crossover, factor addition/removal
5. **Repeat** — Run 24/7 on your machine

```bash
# Crypto (primary use case)
finclaw evolve --market crypto --generations 50

# A-shares
finclaw evolve --market cn --generations 50

# With custom parameters
finclaw evolve --market crypto --population 50 --mutation-rate 0.2 --elite 10
```

### Evolution Results

| Market | Generation | Annual Return | Sharpe | Max Drawdown |
|--------|-----------|---------------|--------|-------------|
| A-Shares | Gen 89 | 2,756% | 6.56 | 26.5% |
| Crypto | Gen 19 | 16,066% | 12.19 | 7.2% |

> ⚠️ **These are in-sample backtest results** on historical data. Real-world performance will be significantly lower. Walk-Forward out-of-sample validation is now enabled by default — always check OOS metrics before trusting any evolved strategy.

---

## Arena Mode (Anti-Overfitting)

Traditional backtesting evaluates each strategy in isolation — overfitted strategies score well on historical data but fail live. FinClaw's **Arena Mode** solves this:

```
┌──────────────────────────────────────────┐
│         Arena: Shared Market Sim          │
│                                           │
│   DNA-1 ──┐                              │
│   DNA-2 ──┤── Same OHLCV data            │
│   DNA-3 ──┤── Same initial capital        │
│   DNA-4 ──┤── Price impact when crowded   │
│   DNA-5 ──┘── Ranked by final P&L        │
│                                           │
│   Overfitted DNA → poor rank → penalized  │
└──────────────────────────────────────────┘
```

- Multiple DNA strategies trade simultaneously in the same simulated market
- **Crowding penalty**: When >50% of DNA strategies buy the same signal, price impact kicks in
- Overfitted strategies that only work in isolation get penalized by arena ranking

---

## Bias Detection

Catch common backtesting pitfalls before trusting results:

```bash
python -m src.evolution.bias_cli --all
```

| Check | What it catches |
|-------|----------------|
| **Look-ahead bias** | Factors that accidentally peek at future data |
| **Data snooping** | DNA that performs 3x+ better on train vs test (overfit) |
| **Survivorship bias** | Assets that delisted during the backtest period |

---

## Validation & Quality

- Walk-forward validation (70/30 train/test split)
- Monte Carlo simulation (1,000 iterations, p-value < 0.05)
- Bootstrap 95% confidence intervals
- Arena competition (multi-DNA market simulation)
- Bias detection (lookahead, snooping, survivorship)
- Factor IC/IR analysis with decay curves
- Factor orthogonality matrix (auto-prune redundant factors)
- Turnover penalty in fitness function
- 5,600+ automated tests

---

## MCP Server (for AI Agents)

Expose FinClaw as tools for Claude, Cursor, VS Code, or any MCP-compatible client:

```json
{
  "mcpServers": {
    "finclaw": {
      "command": "finclaw",
      "args": ["mcp", "serve"]
    }
  }
}
```

10 tools available: `get_quote`, `get_history`, `list_exchanges`, `run_backtest`, `analyze_portfolio`, `get_indicators`, `screen_stocks`, `get_sentiment`, `compare_strategies`, `get_funding_rates`.

---

## Data Sources

| Market | Source | API Key Needed? |
|--------|--------|-----------------|
| Cryptocurrency | ccxt (100+ exchanges) | No (public data) |
| US Stocks | Yahoo Finance | No |
| China A-Shares | AKShare + BaoStock | No |
| News Sentiment | CryptoCompare + AKShare | No |

---

## Dashboard

```bash
cd dashboard && npm install && npm run dev
# Open http://localhost:3000
```

- Real-time prices (Crypto, US stocks, A-Shares)
- TradingView professional charts
- Portfolio tracker with live P&L
- Stock screener with filters + CSV export
- AI chat assistant (OpenAI, Anthropic, DeepSeek, Ollama)

---

## CLI Reference

FinClaw ships with 70+ subcommands. Here are the essentials:

```bash
# Quotes & Data
finclaw quote AAPL              # US stock quote
finclaw quote BTC/USDT          # Crypto quote (via ccxt)
finclaw history NVDA            # Historical data
finclaw download-crypto         # Download crypto OHLCV data
finclaw exchanges list          # Show supported exchanges

# Evolution & Backtesting
finclaw evolve --market crypto  # Run genetic algorithm evolution
finclaw backtest -t AAPL        # Backtest a strategy on a stock
finclaw check-backtest          # Verify backtest results

# Analysis & Tools
finclaw analyze TSLA            # Technical analysis
finclaw screen                  # Stock screener
finclaw risk-report             # Portfolio risk analysis
finclaw sentiment               # Market sentiment
finclaw demo                    # Full feature demo
finclaw doctor                  # Check your environment

# AI Features
finclaw copilot                 # AI financial assistant
finclaw generate-strategy       # Natural language → strategy
finclaw mcp serve               # MCP server for AI agents

# Paper Trading
finclaw paper                   # Paper trading mode
finclaw paper-report            # Paper trading results
```

Run `finclaw --help` for the full list.

---

## Limitations

FinClaw is a research and education tool. Key limitations:

- **Free data sources** — subject to delays, gaps, and API rate limits
- **Simplified backtesting** — does not model order book depth, partial fills, or market microstructure
- **In-sample bias** — evolved strategies may not perform similarly out-of-sample; always check walk-forward OOS results
- **Dry-run first** — always validate strategies with paper trading before risking real capital

For production trading, combine with proper risk management and position sizing.
