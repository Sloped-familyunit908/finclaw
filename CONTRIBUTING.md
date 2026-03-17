# Contributing to FinClaw

Thanks for your interest in contributing! 🦀

## Quick Setup

```bash
git clone https://github.com/NeuZhou/finclaw.git
cd finclaw
pip install -e ".[dev]"
pytest
```

## Development Workflow

1. **Fork & clone** the repo
2. **Create a branch** — `git checkout -b feat/your-feature`
3. **Write tests** — all new features need test coverage
4. **Run the suite** — `pytest` must pass
5. **Lint** — `ruff check src/` must pass
6. **Submit a PR** — describe what and why

## Code Style

- Python 3.9+ compatible
- Type hints on all public functions
- Docstrings on public classes and methods
- No heavy dependencies without discussion (pure NumPy core is intentional)
- Line length: 120 chars (configured in pyproject.toml)

## What We're Looking For

| Area | Description |
|------|-------------|
| 🔌 **Exchange adapters** | Follow `src/exchanges/base.py` ABC |
| 📈 **Strategies** | YAML-configured or Python plugins |
| 📊 **Indicators** | Pure NumPy implementations in `src/ta/` |
| 🐛 **Bug fixes** | Always welcome |
| 📖 **Documentation** | Tutorials, examples, translations |
| 🤖 **AI features** | LLM integrations, strategy generation |

## Project Structure

```
src/
├── cli/         # CLI commands and colors
├── ta/          # Technical indicators (pure NumPy)
├── backtest/    # Backtesting engine
├── paper/       # Paper trading
├── exchanges/   # Multi-exchange adapters
├── strategies/  # Built-in strategy library
├── ai_strategy/ # AI strategy generator & optimizer
├── mcp/         # MCP server for AI agents
└── ...
```

## Testing

```bash
pytest                     # Run all tests
pytest -x                  # Stop on first failure
pytest tests/test_cli.py   # Run specific file
pytest --cov=src           # With coverage
```

## Commit Convention

```
feat: add Kraken WebSocket adapter
fix: correct RSI calculation edge case
docs: update Quick Start example
test: add backtest edge case coverage
refactor: simplify strategy registry
```

## Creating a Strategy Plugin

```bash
finclaw init-strategy my_strategy
cd finclaw-strategy-my_strategy
# Edit strategy.py
pip install -e .
pytest
```

See [examples/](examples/) for reference implementations.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
