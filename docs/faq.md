# FAQ

Common questions and troubleshooting.

---

## General

### What is FinClaw?

FinClaw is an AI-powered quantitative finance engine built on pure NumPy. It provides technical analysis, strategy backtesting, paper trading, portfolio optimization, and crypto/DeFi tools — all in a single Python package with zero heavy dependencies.

### What markets does FinClaw support?

- 🇺🇸 US Stocks (Yahoo Finance, Polygon, Alpha Vantage, Alpaca)
- 🇨🇳 China A-Shares (AkShare, BaoStock, Tushare)
- 🇭🇰 Hong Kong (Yahoo Finance)
- 🇯🇵 Japan (Yahoo Finance)
- 🇰🇷 Korea (Yahoo Finance)
- 🌐 Crypto (Binance, Bybit, OKX, Coinbase, Kraken)

### Is FinClaw free?

Yes. FinClaw is open-source under AGPL-3.0. Free for personal and open-source use. Commercial use requires a separate license.

### Does FinClaw require TA-Lib or pandas?

No. All 17 technical indicators are implemented in pure NumPy. No compiled C libraries, no pandas dependency.

---

## Installation

### `pip install finclaw-ai` fails

Make sure you have Python 3.9+:

```bash
python --version  # Must be 3.9 or higher
pip install --upgrade pip
pip install finclaw-ai
```

### `ModuleNotFoundError: No module named 'yfinance'`

```bash
pip install yfinance
```

Or install FinClaw with all dependencies:

```bash
pip install finclaw-ai[all]
```

### How do I install from source?

```bash
git clone https://github.com/NeuZhou/finclaw.git
cd finclaw
pip install -e ".[dev]"
```

---

## Data

### Why am I getting empty data?

Common causes:
1. **Invalid ticker** — Check the symbol format (e.g., `AAPL` for US, `000001.SZ` for China)
2. **Weekend/holiday** — Markets are closed; recent data may not be available
3. **API rate limit** — Alpha Vantage free tier allows only 25 requests/day
4. **Network issue** — Check your internet connection

### How do I use China A-share data?

```bash
finclaw scan --market china --style buffett
```

AkShare and BaoStock are free and require no API key. For Tushare, set `TUSHARE_TOKEN`.

### How do I clear the cache?

```bash
finclaw cache --clear
```

---

## Strategies

### Which strategy should I start with?

- **Beginners:** Smart DCA or Golden Cross Momentum
- **Intermediate:** RSI Mean Reversion or Bollinger Squeeze
- **Advanced:** Multi-Timeframe Trend or Strategy Combiner

### Can I create my own strategy?

Yes. See the [Plugins guide](plugins.md) for creating custom strategies in Python or YAML.

### What does the AI Debate Arena do?

Multiple AI agents (value, quant, macro, sentiment) analyze a trade opportunity from different angles and debate. The strategy only executes when agents reach consensus above a confidence threshold. This helps avoid trades where technical signals conflict with fundamentals.

---

## Backtesting

### My backtest shows amazing returns. Should I trust it?

Be skeptical. Check for:
- **Overfitting** — FinClaw's deflated Sharpe test can detect this
- **Look-ahead bias** — Walk-forward analysis prevents this
- **Survivorship bias** — Include delisted stocks
- **Small sample** — Need 30+ trades for statistical significance

### How long should a backtest be?

At minimum 3 years to cover different market regimes (bull, bear, sideways). 5+ years is better.

### Why is my backtest slow?

- Reduce the date range
- Use fewer tickers
- Enable caching: `finclaw cache --stats`

---

## Live Trading

### Can FinClaw trade real money?

Paper trading is fully supported. Live broker integration (IBKR, Alpaca) is on the roadmap (v4.0). For now, use FinClaw for signals and execute manually or via Alpaca's API.

### How do I set up paper trading?

```bash
finclaw paper --strategy momentum --ticker BTCUSDT --exchange binance --capital 10000
```

---

## MCP / AI Integration

### Which AI clients support FinClaw?

Any MCP-compatible client: Claude Desktop, Cursor, OpenClaw, VS Code with MCP extensions.

### MCP tools aren't showing up

1. Verify the config path is correct
2. Ensure FinClaw is installed (`pip install -e .`)
3. Restart the AI client after config changes
4. Check logs for import errors

---

## Contributing

### How do I run the tests?

```bash
pip install -e ".[dev]"
pytest
```

1,100+ tests should all pass.

### How do I report a bug?

Open an issue at [github.com/NeuZhou/finclaw/issues](https://github.com/NeuZhou/finclaw/issues).
