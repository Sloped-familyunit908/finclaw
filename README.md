<div align="center">

# 🐋 WhaleTrader

### AI-Powered Quantitative Trading Engine

**The first open-source platform that combines AI agent intelligence with production-grade trading infrastructure.**

[![Rust](https://img.shields.io/badge/engine-Rust-orange?logo=rust)](https://www.rust-lang.org/)
[![Python](https://img.shields.io/badge/strategies-Python-blue?logo=python)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/dashboard-TypeScript-blue?logo=typescript)](https://www.typescriptlang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[Documentation](https://whaletrader.dev/docs) · [Strategy Marketplace](https://whaletrader.dev/marketplace) · [Discord](https://discord.gg/whaletrader)

</div>

---

## Why WhaleTrader?

| Feature | freqtrade | Qlib | nautilus | ai-hedge-fund | **WhaleTrader** |
|---------|:---------:|:----:|:--------:|:--------------:|:---------------:|
| AI-powered analysis | ❌ | ✅ | ❌ | ✅ | ✅ |
| Real exchange trading | ✅ | ❌ | ✅ | ❌ | ✅ |
| Agent Debate Arena | ❌ | ❌ | ❌ | ❌ | ✅ |
| Strategy Marketplace | ❌ | ❌ | ❌ | ❌ | ✅ |
| Natural language strategies | ❌ | ❌ | ❌ | ❌ | ✅ |
| Modern Web Dashboard | ⚠️ | ❌ | ❌ | ❌ | ✅ |
| Multi-asset support | Crypto | Equity | All | Equity | All |
| Production-grade engine | ⚠️ | ❌ | ✅ | ❌ | ✅ |

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     WhaleTrader                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Strategy Layer (Python)                     │ │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────────────┐ │ │
│  │  │Value │ │Macro │ │Momt. │ │Sent. │ │  Community   │ │ │
│  │  │Agent │ │Agent │ │Agent │ │Agent │ │  Strategies  │ │ │
│  │  └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──────┬───────┘ │ │
│  │     └────────┴────────┴────────┴─────────────┘         │ │
│  │                        │                                │ │
│  │              ┌─────────▼─────────┐                      │ │
│  │              │  🏟️ Debate Arena  │  ← Agents debate     │ │
│  │              │  AI Moderator     │    before trading     │ │
│  │              └─────────┬─────────┘                      │ │
│  └────────────────────────┼────────────────────────────────┘ │
│                           │ PyO3                             │
│  ┌────────────────────────▼────────────────────────────────┐ │
│  │              Engine Core (Rust)                          │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐ │ │
│  │  │  Event   │ │  Order   │ │  Risk    │ │ Backtest  │ │ │
│  │  │  Bus     │ │  Manager │ │  Engine  │ │ Engine    │ │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └───────────┘ │ │
│  │  ┌──────────────────────────────────────────────────┐  │ │
│  │  │          Exchange Connectors                     │  │ │
│  │  │  Paper │ Binance │ OKX │ Alpaca │ Interactive B. │  │ │
│  │  └──────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Dashboard (TypeScript / Next.js)           │ │
│  │  Portfolio │ Arena View │ Strategy Lab │ Marketplace    │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

```bash
# Clone the repo
git clone https://github.com/lobster-labs/whale-trader.git
cd whale-trader

# Build the Rust engine
cd engine && cargo build --release && cd ..

# Install Python dependencies
pip install -r requirements.txt

# Run with paper trading (safe, no real money)
whale run --strategy golden-cross-momentum --assets BTC,ETH,SOL --mode paper

# Or describe a strategy in plain English
whale lab "Buy BTC when RSI < 30 and MACD crosses up, sell at 10% profit"
```

## ✨ Key Innovations

### 🏟️ Agent Debate Arena
Multiple AI agents analyze independently, then **debate** their positions before any trade is executed. Watch Warren Buffett argue with a momentum trader in real-time.

### 📦 Strategy Marketplace
Install community strategies with one command. Strategies are defined in a simple YAML format — no coding required for basic strategies.

```bash
whale install golden-cross-ai    # Install a strategy
whale backtest golden-cross-ai   # Backtest it
whale run golden-cross-ai        # Run it (paper mode)
```

### 🧪 Strategy Lab
Describe trading rules in natural language → AI generates executable strategy code → automatic backtesting.

### 📊 Live Dashboard
Real-time portfolio tracking, agent debate visualization, and strategy performance analytics.

## 📁 Project Structure

```
whale-trader/
├── engine/            # 🦀 Rust — High-performance core
│   └── src/
│       ├── core/      # Types, event bus, engine orchestration
│       ├── data/      # Market data providers + indicators
│       ├── exchange/  # Exchange connectors (paper, binance, ...)
│       └── backtest/  # Backtesting engine
├── strategies/        # 🐍 Python — Strategy definitions
│   ├── builtin/       # Built-in strategies (YAML)
│   └── examples/      # Example custom strategies
├── agents/            # 🤖 Python — AI trading agents
├── dashboard/         # ⚡ TypeScript — Next.js web UI
├── sdk/               # 📦 Python SDK & CLI
├── marketplace/       # 🏪 Strategy marketplace logic
└── docs/              # 📖 Documentation
```

## 🗺️ Roadmap

- [x] Core type system & event-driven architecture (Rust)
- [x] Paper trading engine with full P&L tracking (Rust)
- [x] Market data pipeline + technical indicators (Rust)
- [x] Strategy YAML specification + parser (Python)
- [x] Built-in strategy templates
- [ ] AI Agent framework (Python)
- [ ] Agent Debate Arena mechanism
- [ ] Exchange connectors (Binance, OKX)
- [ ] Next.js Dashboard
- [ ] CLI tool (`whale` command)
- [ ] Strategy marketplace
- [ ] Backtesting engine
- [ ] Natural language → strategy generation
- [ ] Community contribution framework

## 💰 Self-Hosted Cost

| Component | Monthly Cost | Notes |
|-----------|:--------:|-------|
| AI inference | $0 | Your own API key / local models |
| Market data | $0 | CoinGecko free tier |
| Hosting | $0 | Runs on your machine |
| **Total** | **$0** | Fully self-hosted |

## Contributing

We welcome contributions! Whether it's a new strategy, a bug fix, or a feature:

1. Fork the repo
2. Create your branch (`git checkout -b feature/amazing-strategy`)
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

**Contributing a strategy is as simple as adding a YAML file** — see `strategies/builtin/` for examples.

## License

MIT — Build on it, ship it, profit.

---

<div align="center">

Built with 🦞 by **Lobster Labs**

*Making professional quantitative trading accessible to everyone.*

</div>
