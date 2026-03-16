# Contributing to FinClaw

Thank you for your interest in contributing! 🦀

## Getting Started

```bash
git clone https://github.com/NeuZhou/finclaw.git
cd finclaw
pip install -e ".[dev]"
pytest
```

## Project Structure

```
finclaw/
├── src/                    # Core library
│   ├── ta/                 # Technical analysis (17 indicators, pure NumPy)
│   ├── strategies/         # 6 strategies + StrategyCombiner
│   ├── backtesting/        # Walk-forward, Monte Carlo, multi-timeframe
│   ├── risk/               # Kelly, VaR, position sizing, stop-loss
│   ├── ml/                 # Feature engine, models, alpha, sentiment
│   ├── portfolio/          # Tracker, rebalancer
│   ├── api/                # REST server + webhooks
│   ├── screener/           # Stock screening
│   ├── alerts/             # Alert engine
│   ├── analytics/          # Attribution, correlation, regime, rolling
│   ├── data/               # Price data providers
│   ├── events/             # Event bus (pub/sub)
│   ├── pipeline/           # Data pipeline, cache, validation
│   ├── optimization/       # Parameter optimization
│   ├── simulation/         # Scenario simulation
│   ├── exchange/           # Paper trading
│   ├── export/             # Report export
│   ├── plugins/            # Plugin manager
│   ├── dashboard/          # Signal dashboard
│   ├── reports/            # HTML/backtest reports
│   └── config.py           # Configuration
├── agents/                 # AI agent layer
├── tests/                  # Test suite (100+ tests)
├── examples/               # Example scripts
├── docs/                   # Documentation
├── finclaw.py              # CLI entry point
├── main.py                 # Main runner
└── pyproject.toml          # Build config
```

## Development Workflow

1. **Fork & branch** from `main`
2. **Write tests** for new features (`tests/`)
3. **Run tests**: `pytest`
4. **Lint**: `ruff check src/ tests/`
5. **Open a PR** with a clear description

## Code Style

- Python 3.9+ with type hints
- No heavy dependencies — NumPy is the only required dep beyond stdlib
- All indicators in `src/ta/` must be pure NumPy
- Use `__all__` exports in `__init__.py`
- Docstrings on all public functions

## Testing

```bash
# Run all tests
pytest

# Run specific module
pytest tests/test_round6.py -v

# Run with coverage
pytest --cov=src
```

## Adding a New Strategy

1. Create `src/strategies/your_strategy.py`
2. Implement `generate_signal(prices, **kwargs)` method
3. Create an adapter class for `StrategyCombiner`
4. Export in `src/strategies/__init__.py`
5. Add tests in `tests/`

## Adding a New Indicator

1. Add function to `src/ta/__init__.py`
2. Pure NumPy only — no TA-Lib or pandas
3. Accept/return `NDArray[np.float64]`
4. Add tests

## License

By contributing, you agree that your contributions will be licensed under AGPL-3.0.
