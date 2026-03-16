# Contributing to FinClaw

Thanks for your interest in contributing to FinClaw! 🦀

## Getting Started

```bash
git clone https://github.com/NeuZhou/finclaw.git
cd finclaw
pip install -e ".[dev]"
pytest
```

## Development Workflow

1. **Fork & clone** the repository
2. **Create a branch** — `git checkout -b feat/your-feature`
3. **Write tests** — We maintain 1,100+ tests. New features need tests.
4. **Run the suite** — `pytest` (all tests must pass)
5. **Submit a PR** — Describe what and why

## Code Style

- Python 3.9+ compatible
- Type hints on all public functions
- Docstrings on all public classes and methods
- No heavy dependencies without discussion (pure NumPy core is intentional)

## What We're Looking For

- 🔌 **New exchange adapters** — Follow the ABC in `src/exchanges/base.py`
- 🤖 **New strategies** — YAML-configured, add to `strategies/builtin/`
- 📊 **New indicators** — Pure NumPy implementations in `src/ta/`
- 🐛 **Bug fixes** — Always welcome
- 📝 **Documentation** — Tutorials, examples, translations

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the system design overview.

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific module
pytest tests/test_exchanges.py
```

## Commit Convention

```
feat: add Kraken WebSocket adapter
fix: correct RSI calculation edge case
docs: update Quick Start example
test: add backtest edge case coverage
```

## License

By contributing, you agree that your contributions will be licensed under AGPL-3.0.
