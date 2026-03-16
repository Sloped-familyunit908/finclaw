# Contributing to FinClaw 🐋

Thank you for your interest in contributing!

## Getting Started

### Prerequisites

- Python 3.9+
- pip

### Setup

```bash
git clone https://github.com/NeuZhou/finclaw.git
cd finclaw
pip install -r requirements.txt
pip install pytest pytest-asyncio ruff
```

### Verify

```bash
python -m pytest tests/ -v
```

## How to Contribute

### 🐛 Bug Reports

Open an issue with:
- Steps to reproduce
- Expected vs actual behavior
- Python version, OS

### 🎯 Strategy Contributions

Add a new trading strategy:

1. Add selection logic to `finclaw.py` STRATEGIES dict
2. Add tests in `tests/`
3. Run benchmarks: `python benchmark_real.py`
4. Submit PR with backtest results

### 🧪 Tests

We have 100+ tests. All PRs must pass:

```bash
python -m pytest tests/ -v --tb=short
```

Add tests for any new feature. Use `tests/conftest.py` fixtures for synthetic price data.

### 🤖 Agent Plugins

Create custom AI agent personalities in `agents/`:

1. Add your agent profile to `agents/registry.py`
2. Follow the `AgentProfile` dataclass pattern
3. Add tests

### 📊 Data Sources

Add support for new market data providers:

1. Implement in `agents/` or `src/data/`
2. Add tests with mock data
3. Document in README

## Code Style

- **Python**: Follow PEP 8, use type hints
- **Lint**: `ruff check . --select E,F,W --ignore E501`
- **Tests**: pytest, use fixtures from `conftest.py`
- **Commits**: Conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `ci:`)

## Pull Request Process

1. Fork the repo
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make changes, add tests
4. Run `python -m pytest tests/ -v`
5. Run `ruff check .`
6. Commit with conventional message
7. Push and open PR

## Project Structure

```
finclaw/
├── finclaw.py          # CLI entry point
├── agents/             # Signal engines, backtester, stock picker
├── strategies/         # Strategy definitions
├── tests/              # 100+ pytest tests
├── mcp_server.py       # MCP protocol server
├── telegram_bot.py     # Telegram interface
└── daily_alert.py      # Daily alerts
```

## Code of Conduct

Be kind, be constructive, be collaborative.

## License

By contributing, you agree that your contributions will be licensed under [AGPL-3.0](LICENSE).

## 🌐 Related Tools for Contributors

- **[ClawGuard](https://github.com/NeuZhou/clawguard)** — Scan for security vulnerabilities in AI agent code
- **[AgentProbe](https://github.com/NeuZhou/agentprobe)** — Test framework for AI agent tools
- **[repo2skill](https://github.com/NeuZhou/repo2skill)** — Convert repos into AI agent skills
