# Contributing to WhaleTrader

Thank you for considering contributing to WhaleTrader! 🐋

## Quick Links

- [Strategy Contribution Guide](docs/ECOSYSTEM.md#1-contribute-a-strategy)
- [Agent Plugin Guide](docs/ECOSYSTEM.md#2-create-an-agent-plugin)
- [Data Connector Guide](docs/ECOSYSTEM.md#3-add-a-data-connector)
- [Research Foundation](docs/RESEARCH.md)

## Getting Started

### Prerequisites
- **Rust 1.80+** — For the engine core
- **Python 3.11+** — For strategies and AI agents
- **Node.js 20+** — For the dashboard (optional)

### Development Setup

```bash
# Clone
git clone https://github.com/lobster-labs/whale-trader.git
cd whale-trader

# Build Rust engine
cd engine && cargo build && cargo test && cd ..

# Install Python deps
pip install -r requirements.txt

# Run the demo
python whale.py
```

## Contribution Types

### 🎯 Strategy (Easiest — Just YAML!)

The fastest way to contribute. No Rust, no complex Python:

1. Create `strategies/community/your-strategy-name.yaml`
2. Follow the [YAML spec](strategies/builtin/golden-cross-momentum.yaml)
3. Submit a PR
4. Our CI will auto-backtest and add results

### 🤖 Agent Plugin (Python)

Create a custom AI agent personality:

1. Create `agents/plugins/your_agent.py`
2. Define an `AgentProfile` with name, role, and system prompt
3. Submit a PR

### 🔧 Engine Enhancement (Rust)

For performance-critical features:

1. Work in `engine/src/`
2. Run `cargo test` — all tests must pass
3. Run `cargo clippy` — no warnings
4. Submit a PR

### 📊 Data Source (Rust/Python)

Add a new market data provider:

1. Implement the data source interface
2. Add tests with mock data
3. Submit a PR

## Code Style

### Rust
- Follow standard Rust conventions
- Use `cargo fmt` before committing
- All public APIs must have doc comments

### Python
- Follow PEP 8
- Type hints required for all function signatures
- Docstrings for all public functions

### Commit Messages
```
feat(agents): add sentiment analysis agent
fix(engine): correct RSI calculation for short series
docs(strategy): add MACD crossover strategy example
```

## Code of Conduct

Be kind, be constructive, be collaborative.
We're building something cool together.

## License

By contributing, you agree that your contributions will be licensed
under the MIT License.
