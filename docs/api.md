# FinClaw API Reference

> Version 5.1.0 — Complete API documentation for FinClaw's programmatic interfaces.

---

## Table of Contents

- [CLI Reference](#cli-reference)
- [Python API](#python-api)
- [Strategy API](#strategy-api)
- [Exchange Adapter API](#exchange-adapter-api)
- [Plugin System API](#plugin-system-api)
- [AI Strategy Generator API](#ai-strategy-generator-api)
- [MCP Server](#mcp-server)
- [BTC Metrics & Crypto Tools](#btc-metrics--crypto-tools)
- [A2A Protocol](#a2a-protocol)

---

## CLI Reference

FinClaw uses argparse-based subcommands. Run `finclaw --help` for the full list.

### Core Commands

| Command | Description | Example |
|---------|-------------|---------|
| `quote` | Real-time quotes from any exchange | `finclaw quote AAPL TSLA --exchange yahoo` |
| `analyze` | Technical analysis with indicators | `finclaw analyze --ticker AAPL --indicators rsi,macd,bollinger` |
| `backtest` | Strategy backtesting | `finclaw backtest -t AAPL,MSFT -s momentum --start 2023-01-01` |
| `chart` | Terminal charts (candle/line/bar/histogram) | `finclaw chart AAPL --type candle --period 6mo` |
| `price` | Current prices for multiple tickers | `finclaw price --ticker AAPL,MSFT,GOOGL` |
| `screen` | Screen stocks by criteria | `finclaw screen --criteria "rsi<30,pe<15" --universe sp500` |
| `compare` | Compare multiple strategies | `finclaw compare -s momentum,mean_reversion -d AAPL -p 1y` |
| `export` | Export OHLCV + indicators to CSV/JSON | `finclaw export -t AAPL -p 1y -f csv -i sma20,rsi,macd` |
| `demo` | Showcase all features (no API key needed) | `finclaw demo` |
| `info` | Show system info and version | `finclaw info` |

### Paper Trading

| Command | Description | Example |
|---------|-------------|---------|
| `paper start` | Start a paper trading session | `finclaw paper start --balance 100000` |
| `paper buy` | Buy shares | `finclaw paper buy AAPL 50` |
| `paper sell` | Sell shares | `finclaw paper sell MSFT 20` |
| `paper portfolio` | Show portfolio | `finclaw paper portfolio` |
| `paper pnl` | Show P&L | `finclaw paper pnl` |
| `paper history` | Show trade history | `finclaw paper history` |
| `paper dashboard` | Visual dashboard | `finclaw paper dashboard` |
| `paper run-strategy` | Run a strategy | `finclaw paper run-strategy golden-cross --symbols AAPL,MSFT` |
| `paper journal` | Trade journal (exportable) | `finclaw paper journal --export csv` |
| `paper reset` | Reset session | `finclaw paper reset` |

### Strategy Library

| Command | Description | Example |
|---------|-------------|---------|
| `strategy list` | List all built-in + YAML strategies | `finclaw strategy list` |
| `strategy info` | Show strategy details | `finclaw strategy info grid-trading` |
| `strategy backtest` | Backtest a built-in strategy | `finclaw strategy backtest trend-following --symbol AAPL` |
| `strategy create` | Interactive YAML strategy builder | `finclaw strategy create` |
| `strategy validate` | Validate a YAML strategy file | `finclaw strategy validate my_strategy.yaml` |
| `strategy dsl-backtest` | Backtest a YAML strategy | `finclaw strategy dsl-backtest my_strategy.yaml -s AAPL` |
| `strategy optimize` | Grid-search parameter optimization | `finclaw strategy optimize strat.yaml --param rsi_period:10:30:5 -s AAPL` |

### AI Features

| Command | Description | Example |
|---------|-------------|---------|
| `generate-strategy` | AI-generate strategy from description | `finclaw generate-strategy "buy when RSI < 30 and MACD golden cross"` |
| `optimize-strategy` | AI-optimize existing strategy | `finclaw optimize-strategy my_strategy.py --data AAPL` |
| `copilot` | Interactive AI financial assistant | `finclaw copilot` |

**Flags for `generate-strategy`:**

- `--market` — Target market: `us_stock`, `crypto`, `cn_stock` (default: `us_stock`)
- `--risk` — Risk profile: `low`, `medium`, `high` (default: `medium`)
- `--provider` — LLM provider: `openai`, `anthropic`, `deepseek`, `ollama`, `groq`, `mistral`, `moonshot`
- `--output` — Save generated code to file
- `--interactive` — Multi-turn interactive builder

### Crypto & BTC Tools

| Command | Description | Example |
|---------|-------------|---------|
| `btc-metrics` | BTC on-chain metrics dashboard | `finclaw btc-metrics` |
| `funding-rates` | Multi-exchange funding rate comparison | `finclaw funding-rates --symbols BTCUSDT,ETHUSDT,SOLUSDT` |
| `fear-greed` | Fear & Greed Index with history | `finclaw fear-greed --history 7` |

**Flags for `funding-rates`:**

- `--symbols` — Comma-separated symbols (default: `BTCUSDT,ETHUSDT,SOLUSDT`)
- `--min-spread` — Minimum annualized spread % for arbitrage alerts (default: `5.0`)

### Exchanges

| Command | Description | Example |
|---------|-------------|---------|
| `exchanges list` | List all exchange adapters | `finclaw exchanges list` |
| `exchanges compare` | Feature comparison table | `finclaw exchanges compare yahoo binance` |
| `history` | Get OHLCV candles from any exchange | `finclaw history AAPL -e yahoo -t 1d -l 20` |

### Alerts

| Command | Description | Example |
|---------|-------------|---------|
| `alert add` | Add alert rule | `finclaw alert add -s AAPL --price-above 200` |
| `alert list` | List active rules | `finclaw alert list` |
| `alert remove` | Remove a rule by ID | `finclaw alert remove 1` |
| `alert history` | Show triggered alerts | `finclaw alert history --hours 24` |
| `alert start` | Start alert engine | `finclaw alert start -s AAPL,TSLA --interval 60` |

**Alert conditions:** `--price-above`, `--price-below`, `--rsi-above`, `--rsi-below`, `--volume-spike`, `--macd-cross`, `--bb-breakout`, `--drawdown`

### Sentiment & News

| Command | Description | Example |
|---------|-------------|---------|
| `sentiment` | Sentiment analysis for a symbol | `finclaw sentiment TSLA --reddit` |
| `news` | Financial news | `finclaw news AAPL --limit 10` |
| `trending` | Trending topics & WSB tickers | `finclaw trending` |
| `scan` | Real-time market scanner | `finclaw scan --rule "rsi<30 AND volume>2x" --symbols AAPL,TSLA` |

### Other

| Command | Description | Example |
|---------|-------------|---------|
| `risk` | Portfolio risk analysis (VaR, Sharpe, etc.) | `finclaw risk --portfolio portfolio.json` |
| `portfolio track` | Track portfolio from JSON file | `finclaw portfolio track --file portfolio.json` |
| `options price` | Black-Scholes option pricing | `finclaw options price --type call --S 150 --K 155 --T 0.5 --r 0.05 --sigma 0.25` |
| `report` | Generate HTML/JSON report | `finclaw report --input results.json --format html` |
| `tearsheet` | QuantStats-style tearsheet | `finclaw tearsheet --returns returns.csv --benchmark SPY` |
| `watchlist create` | Create/manage watchlists | `finclaw watchlist create tech AAPL MSFT GOOGL` |
| `predict run` | ML prediction | `finclaw predict run --symbol AAPL --model gradient-boost` |
| `predict backtest` | Walk-forward ML backtest | `finclaw predict backtest --symbol AAPL --model random-forest` |
| `plugin list` | List installed plugins | `finclaw plugin list` |
| `plugin install` | Install a plugin file | `finclaw plugin install my_plugin.py` |
| `plugin create` | Create plugin from template | `finclaw plugin create --type strategy --name my_strat` |
| `init-strategy` | Generate strategy plugin scaffolding | `finclaw init-strategy my_strategy` |
| `serve` | Start REST API server | `finclaw serve --port 8080 --auth` |
| `mcp serve` | Start MCP server (stdio) | `finclaw mcp serve` |
| `mcp config` | Generate MCP client config | `finclaw mcp config --client claude` |
| `a2a serve` | Start A2A protocol server | `finclaw a2a serve --port 8081` |
| `a2a card` | Print A2A agent card | `finclaw a2a card` |
| `cache` | Cache management | `finclaw cache --stats` / `finclaw cache --clear` |
| `interactive` | Interactive REPL mode | `finclaw interactive` |

---

## Python API

```python
from finclaw import FinClaw

fc = FinClaw()

# Quote
quote = fc.quote("AAPL")
print(f"AAPL: ${quote['price']:.2f} ({quote['change_pct']:+.1f}%)")

# Backtest
result = fc.backtest(strategy="momentum", ticker="NVDA", start="2023-01-01")
print(f"Return: {result.total_return:.1%} | Sharpe: {result.sharpe_ratio:.2f}")
```

### Exchange Adapters (Python)

```python
from src.exchanges.registry import ExchangeRegistry

# List available exchanges
ExchangeRegistry.list_exchanges()       # all
ExchangeRegistry.list_by_type("crypto") # crypto only

# Get an adapter and use it
adapter = ExchangeRegistry.get("binance")
ticker = adapter.get_ticker("BTCUSDT")
candles = adapter.get_ohlcv("ETHUSDT", "1h", limit=100)
```

### Technical Indicators (Python)

```python
from src.ta import rsi, macd, sma, ema

import numpy as np
prices = np.array([...], dtype=np.float64)

rsi_values = rsi(prices, period=14)
macd_line, signal_line, histogram = macd(prices)
sma_20 = sma(prices, 20)
ema_12 = ema(prices, 12)
```

---

## Strategy API

### Built-in Strategies

FinClaw ships with 20+ built-in strategies in two systems:

**Strategy Library** (`src/strategies/library/`):
- `trend-following` — SMA crossover trend following
- `mean-reversion-bb` — Bollinger Band mean reversion
- `grid-trading` — Grid trading for range-bound markets
- `breakout` — Price breakout detection
- `btc-cycle` — BTC halving cycle strategy
- `dca` — Dollar cost averaging
- `dividend-harvest` — Dividend capture
- `funding-rate` — Crypto funding rate arbitrage
- `multi-factor` — Multi-factor model
- `pairs-trading` — Statistical arbitrage pairs
- `sector-rotation` — Sector rotation

**Core Strategies** (`src/strategies/`):
- `momentum_jt` — Jegadeesh-Titman momentum
- `mean_reversion` — Statistical mean reversion
- `trend_following` — Classic trend following
- `crypto_strategies` — Crypto-specific strategies
- `regime_adaptive` — Regime-adaptive strategy
- `value_momentum` — Value + momentum combo
- `pairs_trading` — Pairs trading
- `sector_rotation` — Sector rotation
- `signal_combiner` — Multi-signal combination

### Writing Custom Strategies

Create a class inheriting from `StrategyPlugin`:

```python
from src.plugin_system.plugin_types import StrategyPlugin
import pandas as pd

class MyStrategy(StrategyPlugin):
    name = "my_strategy"
    version = "1.0.0"
    description = "My custom strategy"
    markets = ["us_stock", "crypto"]
    risk_level = "medium"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Return Series with 1=buy, -1=sell, 0=hold."""
        signals = pd.Series(0, index=data.index)
        # Your logic here
        close = data["Close"]
        sma20 = close.rolling(20).mean()
        sma50 = close.rolling(50).mean()
        signals[sma20 > sma50] = 1
        signals[sma20 < sma50] = -1
        return signals

    def get_parameters(self) -> dict:
        return {"fast_period": 20, "slow_period": 50}
```

Use it:

```bash
# As a plugin
finclaw backtest --strategy plugin:my_strategy -t AAPL

# Register programmatically
from src.plugin_system.registry import StrategyRegistry
registry = StrategyRegistry()
registry.register(MyStrategy())
```

### YAML Strategy DSL

Define strategies in YAML without writing Python:

```yaml
name: Golden Cross RSI Filter
description: Buy on golden cross when RSI confirms
universe: sp500
entry:
  - sma(20) > sma(50)
  - rsi(14) < 70
exit:
  - sma(20) < sma(50)
risk:
  stop_loss: 5%
  take_profit: 15%
  max_position: 10%
rebalance: weekly
```

```bash
finclaw strategy validate my_strategy.yaml
finclaw strategy dsl-backtest my_strategy.yaml --symbol AAPL --period 2y
finclaw strategy optimize my_strategy.yaml --param rsi_period:10:30:5 --symbol AAPL
```

### Multi-Strategy Voting

Combine multiple strategies with majority voting:

```python
from src.plugin_system.registry import StrategyRegistry

registry = StrategyRegistry()
registry.load_all()

# Majority voting across strategies
combined_signals = registry.vote(
    ["trend_following", "mean_reversion", "momentum"],
    data,
    threshold=0.5,  # >50% must agree
)
```

---

## Exchange Adapter API

### Supported Exchanges

| Exchange | Type | OHLCV | Ticker | Orderbook | WebSocket | Funding Rates |
|----------|------|-------|--------|-----------|-----------|---------------|
| **Yahoo Finance** | stock_us | ✅ | ✅ | — | — | — |
| **Binance** | crypto | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Bybit** | crypto | ✅ | ✅ | ✅ | ✅ | ✅ |
| **OKX** | crypto | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Coinbase** | crypto | ✅ | ✅ | ✅ | — | — |
| **Kraken** | crypto | ✅ | ✅ | ✅ | — | — |
| **Alpaca** | stock_us | ✅ | ✅ | — | — | — |
| **Polygon** | stock_us | ✅ | ✅ | — | — | — |
| **Alpha Vantage** | stock_us | ✅ | ✅ | — | — | — |
| **AkShare** | stock_cn | ✅ | ✅ | — | — | — |
| **BaoStock** | stock_cn | ✅ | ✅ | — | — | — |
| **Tushare** | stock_cn | ✅ | ✅ | — | — | — |

### Writing a Custom Exchange Adapter

Inherit from `ExchangeAdapter`:

```python
from src.exchanges.base import ExchangeAdapter

class MyExchangeAdapter(ExchangeAdapter):
    exchange_type = "crypto"  # or "stock_us", "stock_cn"

    def get_ticker(self, symbol: str) -> dict:
        """Return {"symbol", "last", "bid", "ask", "volume", ...}"""
        ...

    def get_ohlcv(self, symbol: str, timeframe: str = "1d", limit: int = 100) -> list[dict]:
        """Return list of {"open", "high", "low", "close", "volume", "timestamp"}"""
        ...

    def get_orderbook(self, symbol: str, depth: int = 20) -> dict:
        """Return {"bids": [[price, qty], ...], "asks": [[price, qty], ...]}"""
        ...

    def place_order(self, symbol: str, side: str, order_type: str, quantity: float, price: float = None) -> dict:
        ...

    def cancel_order(self, order_id: str) -> dict:
        ...

    def get_balance(self) -> dict:
        ...
```

Register it:

```python
from src.exchanges.registry import ExchangeRegistry
ExchangeRegistry.register("my_exchange", MyExchangeAdapter())
```

### HTTP Client Utility

All exchange adapters use a shared HTTP client with retry and error handling:

```python
from src.exchanges.http_client import HttpClient

client = HttpClient("https://api.example.com", timeout=10)
data = client.get("/endpoint", params={"key": "value"})
```

---

## Plugin System API

### Plugin Types

FinClaw supports three plugin types:

1. **Strategy Plugins** — Trading strategies (`StrategyPlugin`)
2. **Indicator Plugins** — Custom technical indicators (`IndicatorPlugin`)
3. **Exchange Plugins** — Custom exchange adapters (`ExchangePlugin`)

### Strategy Plugin Scaffold

```bash
finclaw init-strategy my_awesome_strategy
# Creates finclaw-strategy-my_awesome_strategy/ with template files

cd finclaw-strategy-my_awesome_strategy
pip install -e .
finclaw backtest --strategy plugin:my_awesome_strategy -t AAPL
```

### Plugin Manager

```python
from src.plugins.manager import PluginManager

pm = PluginManager()
pm.discover()  # Auto-discover plugins
pm.list_plugins()
pm.get_plugin("my_plugin")
```

### Backtrader Compatibility

FinClaw can load Backtrader strategies via an adapter:

```python
from src.plugin_system.backtrader_adapter import BacktraderAdapter

# Wrap a Backtrader strategy class
adapter = BacktraderAdapter(MyBacktraderStrategy)
signals = adapter.generate_signals(data)
```

### TA-Lib Integration

Use TA-Lib indicators alongside FinClaw's built-in ones:

```python
from src.plugin_system.talib_adapter import TaLibAdapter

# Wraps TA-Lib functions into FinClaw's indicator interface
ta = TaLibAdapter()
rsi = ta.indicator("RSI", prices, timeperiod=14)
macd, signal, hist = ta.indicator("MACD", prices)
```

### Pine Script Parser

Basic Pine Script compatibility for simple scripts:

```python
from src.plugin_system.pine_parser import PineParser

parser = PineParser()
strategy = parser.parse("pine_strategy.pine")
signals = strategy.generate_signals(data)
```

---

## AI Strategy Generator API

### Generate from Natural Language

```python
from src.ai_strategy.strategy_generator import StrategyGenerator

gen = StrategyGenerator(market="us_stock", risk="medium")

# Sync
result = gen.generate("buy when RSI < 30 and MACD golden cross")
print(result["code"])       # Generated Python code
print(result["class_name"]) # Strategy class name
print(result["valid"])      # True if code passes validation

# Async
result = await gen.generate_async("momentum strategy on volume spikes")
```

### Supported LLM Providers

Set any of these environment variables:
- `OPENAI_API_KEY` — OpenAI (GPT-4, etc.)
- `ANTHROPIC_API_KEY` — Anthropic (Claude)
- `DEEPSEEK_API_KEY` — DeepSeek
- `GEMINI_API_KEY` — Google Gemini
- `GROQ_API_KEY` — Groq
- `MISTRAL_API_KEY` — Mistral
- `MOONSHOT_API_KEY` — Moonshot

Or use a local Ollama instance (auto-detected).

### AI Copilot

```python
from src.ai_strategy.copilot import FinClawCopilot

copilot = FinClawCopilot()
copilot.run_interactive()
# > 分析特斯拉最近走势
# > 帮我创建一个均值回归策略
```

### AI Strategy Optimizer

```python
from src.ai_strategy.strategy_optimizer import StrategyOptimizer

optimizer = StrategyOptimizer(provider_name="openai")
result = optimizer.analyze(strategy_code, backtest_results)
# Returns: analysis, suggestions (parameter tuning), risk_assessment
```

---

## MCP Server

FinClaw exposes its capabilities as MCP (Model Context Protocol) tools for AI agents like Claude, Cursor, VS Code Copilot, and OpenClaw.

### Start the Server

```bash
finclaw mcp serve
```

### Client Configuration

```bash
finclaw mcp config --client claude    # Generate config for Claude Desktop
finclaw mcp config --client cursor    # Generate config for Cursor
finclaw mcp config --client openclaw  # Generate config for OpenClaw
finclaw mcp config --client vscode    # Generate config for VS Code
```

Example Claude Desktop config (`claude_desktop_config.json`):

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

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `get_quote` | Real-time quote for any symbol |
| `get_history` | OHLCV candle history |
| `list_exchanges` | List available exchange adapters |
| `run_backtest` | Run strategy backtest |
| `analyze_portfolio` | Portfolio analysis with risk metrics |
| `get_indicators` | Calculate technical indicators (SMA, EMA, RSI, MACD, BBands) |
| `screen_stocks` | Screen stocks by technical/fundamental criteria |
| `get_sentiment` | Market sentiment analysis |
| `compare_strategies` | Compare multiple strategies |
| `get_funding_rates` | Crypto funding rates |

### MCP Tool Schema Example

```json
{
  "name": "get_quote",
  "description": "Get a real-time quote for a symbol from any supported exchange.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "symbol": {"type": "string", "description": "Ticker symbol, e.g. AAPL, BTCUSDT"},
      "exchange": {"type": "string", "default": "yahoo"}
    },
    "required": ["symbol"]
  }
}
```

---

## BTC Metrics & Crypto Tools

### BTC On-Chain Metrics

```python
from src.crypto.btc_metrics import BTCMetricsClient

client = BTCMetricsClient()

# On-chain metrics (hashrate, difficulty, mempool, fees)
metrics = client.get_onchain_metrics()

# MVRV Ratio (market cap vs realized cap)
mvrv = client.get_mvrv_ratio()

# Miner outflow tracking
miner = client.get_miner_outflow()

# Fear & Greed Index
fg = client.get_fear_greed(limit=7)
```

**Data sources:** Blockchain.info (chain stats), Alternative.me (Fear & Greed).

### Multi-Exchange Funding Dashboard

```python
from src.crypto.funding_dashboard import FundingDashboardClient

client = FundingDashboardClient()

# Get rates from Binance, Bybit, OKX
rates = client.get_all_rates(["BTCUSDT", "ETHUSDT", "SOLUSDT"])

# Full dashboard with arbitrage opportunities
dashboard = client.get_dashboard(min_spread=5.0)
for arb in dashboard.arbitrage_opportunities:
    print(f"{arb.symbol}: Long {arb.long_exchange} → Short {arb.short_exchange} = {arb.spread}% spread")
```

### Lightning Network Monitor

```python
from src.crypto.lightning import LightningMonitor

ln = LightningMonitor()

# Network stats (capacity, nodes, channels, fees)
stats = ln.get_network_stats()

# Top nodes by capacity
nodes = ln.get_top_nodes(limit=10)
```

### Other Crypto Modules

- **`src.crypto.onchain`** — On-chain analytics
- **`src.crypto.liquidation_tracker`** — Liquidation tracking
- **`src.crypto.rebalancer`** — Portfolio rebalancing for crypto

---

## A2A Protocol

FinClaw supports the Agent-to-Agent (A2A) protocol for inter-agent communication.

```bash
finclaw a2a serve --port 8081        # Start A2A server
finclaw a2a card                      # Print agent card
```

Agent card endpoint: `http://localhost:8081/.well-known/agent.json`

```python
from src.a2a.server import run_server
import asyncio

asyncio.run(run_server(host="localhost", port=8081, auth_token="secret"))
```

---

## REST API Server

```bash
finclaw serve --port 8080 --auth --rate-limit 100
```

Starts an HTTP API server exposing FinClaw's functionality. Use `--auth` to require API key authentication.

---

## Configuration

FinClaw uses `~/.finclaw/` for persistent state:

| File | Purpose |
|------|---------|
| `~/.finclaw/config.yaml` | Global configuration |
| `~/.finclaw/cache/` | Data cache |
| `~/.finclaw/paper_state.json` | Paper trading session |
| `~/.finclaw/paper_journal.json` | Trade journal |
| `~/.finclaw/alert_rules.json` | Alert rules |
| `~/.finclaw/alert_history.json` | Alert history |
| `~/.finclaw/watchlists/` | Saved watchlists |

Project-level config: `finclaw.yml` in the project root.
