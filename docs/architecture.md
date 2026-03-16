# FinClaw Architecture

> System architecture for FinClaw v3.7.0

## High-Level Overview

```mermaid
graph TB
    CLI[CLI / Interactive] --> Engine[Signal Engine]
    API[REST API] --> Engine
    MCP[MCP Server] --> Engine
    Telegram[Telegram Bot] --> Engine
    
    Engine --> Strategies[Strategy Layer]
    Engine --> ML[ML Models]
    Engine --> TA[Technical Analysis]
    Engine --> Data[Data Layer]
    
    Strategies --> Backtesting[Backtesting Engine]
    Strategies --> PaperTrading[Paper Trading]
    Strategies --> Risk[Risk Management]
    
    Data --> YFinance[yfinance]
    Data --> Cache[(SQLite Cache)]
    Data --> Streaming[WebSocket Stream]
    
    Risk --> Portfolio[Portfolio Manager]
    Risk --> Alerts[Alert Engine]
    
    Backtesting --> Reports[Report Generator]
    Reports --> HTML[HTML Reports]
    Reports --> PDF[PDF Reports]
    
    Engine --> Events[Event Bus]
    Events --> Plugins[Plugin System]
    Events --> Webhooks[Webhooks]
```

## Module Dependency Graph

```mermaid
graph LR
    subgraph Core
        TA[src/ta]
        Data[src/data]
        Config[src/config]
        Events[src/events]
    end
    
    subgraph Strategy
        Strat[src/strategies]
        ML[src/ml]
        Crypto[src/strategies/crypto]
    end
    
    subgraph Execution
        BT[src/backtesting]
        Trading[src/trading]
        Risk[src/risk]
        Exec[src/execution]
    end
    
    subgraph Output
        Reports[src/reports]
        Dashboard[src/dashboard]
        Export[src/export]
        Notif[src/notifications]
    end
    
    subgraph Extensions
        Plugins[src/plugins]
        API[src/api]
        Deriv[src/derivatives]
        DeFi[src/defi]
    end
    
    Data --> TA
    TA --> Strat
    TA --> ML
    Strat --> BT
    Strat --> Trading
    ML --> Strat
    Risk --> BT
    Risk --> Trading
    BT --> Reports
    Events --> Plugins
    Config --> Data
    Config --> BT
    Exec --> Trading
```

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant DataRouter
    participant Cache
    participant YFinance
    participant Strategy
    participant Backtester
    participant RiskMgr
    participant Reporter

    User->>CLI: finclaw backtest --tickers AAPL
    CLI->>DataRouter: fetch("AAPL", period="5y")
    DataRouter->>Cache: check cache
    alt Cache hit
        Cache-->>DataRouter: cached data
    else Cache miss
        DataRouter->>YFinance: download
        YFinance-->>DataRouter: OHLCV data
        DataRouter->>Cache: store
    end
    DataRouter-->>CLI: price data
    CLI->>Strategy: generate_signals(prices)
    Strategy-->>CLI: signals[]
    CLI->>Backtester: run(signals, prices)
    Backtester->>RiskMgr: check_limits()
    RiskMgr-->>Backtester: approved
    Backtester-->>CLI: BacktestResult
    CLI->>Reporter: generate(result)
    Reporter-->>User: HTML report
```

## Event System

FinClaw uses a publish/subscribe event bus for decoupled communication.

```mermaid
graph TB
    subgraph Producers
        Market[Market Data]
        Strategy[Strategy Engine]
        Orders[Order Manager]
        Fills[Fill Engine]
    end
    
    subgraph EventBus[Event Bus]
        direction TB
        ME[MarketEvent]
        SE[SignalEvent]
        OE[OrderEvent]
        FE[FillEvent]
    end
    
    subgraph Consumers
        Logger[Trade Logger]
        Risk[Risk Monitor]
        Dashboard[Dashboard]
        Webhook[Webhook Notifier]
        Journal[Trade Journal]
    end
    
    Market --> ME
    Strategy --> SE
    Orders --> OE
    Fills --> FE
    
    ME --> Strategy
    SE --> Orders
    OE --> Fills
    FE --> Logger
    FE --> Risk
    FE --> Dashboard
    FE --> Webhook
    FE --> Journal
```

### Event Types

| Event | Payload | Emitted By |
|-------|---------|------------|
| `MarketEvent` | OHLCV bar | Data layer |
| `SignalEvent` | ticker, action, confidence | Strategy |
| `OrderEvent` | ticker, side, quantity, type | Order router |
| `FillEvent` | ticker, price, quantity, commission | Execution |

## Plugin Architecture

```mermaid
graph TB
    PM[PluginManager] --> Discover[discover plugins/]
    PM --> Load[load & validate]
    PM --> Registry[Plugin Registry]
    
    Registry --> StratPlugins[Strategy Plugins]
    Registry --> DataPlugins[Data Source Plugins]
    Registry --> IndPlugins[Indicator Plugins]
    Registry --> ExpPlugins[Exporter Plugins]
    
    subgraph Plugin Contract
        Register["register(manager)"]
        Meta["name, version, type"]
    end
    
    Load --> Register
```

### Plugin Types

| Type | Interface | Example |
|------|-----------|---------|
| `strategy` | `generate_signal(prices) → str` | Custom momentum variant |
| `data_source` | `fetch(ticker, period) → DataFrame` | Alternative data provider |
| `indicator` | `calculate(data) → Array` | Custom TA indicator |
| `exporter` | `export(result) → None` | CSV/Parquet exporter |

### Writing a Plugin

```python
# plugins/my_plugin.py

def register(manager):
    """Called by PluginManager on load."""
    manager.add_strategy("my_strategy", MyStrategy)
    manager.add_indicator("my_indicator", my_indicator_fn)
```

## Directory Structure

```
finclaw/
├── src/
│   ├── ta/              # Technical analysis (17 indicators)
│   ├── strategies/      # Trading strategies (9 strategies)
│   ├── ml/              # Machine learning models
│   ├── backtesting/     # Backtesting engines
│   ├── risk/            # Risk management
│   ├── data/            # Data fetching & caching
│   ├── events/          # Event bus (pub/sub)
│   ├── plugins/         # Plugin system
│   ├── analytics/       # Performance analytics
│   ├── portfolio/       # Portfolio tracking
│   ├── reports/         # Report generation
│   ├── dashboard/       # Interactive dashboards
│   ├── api/             # REST API + webhooks
│   ├── execution/       # Order routing
│   ├── trading/         # Paper trading
│   ├── derivatives/     # Options pricing
│   ├── crypto/          # On-chain analytics
│   ├── defi/            # DeFi yield tracking
│   ├── screener/        # Stock screener
│   ├── alerts/          # Alert engine
│   ├── notifications/   # Webhook notifications
│   ├── export/          # Data export
│   ├── sandbox/         # Strategy sandbox
│   ├── simulation/      # Scenario simulation
│   ├── journal/         # Trade journal
│   ├── watchlist/       # Watchlist manager
│   ├── fixed_income/    # Yield curve
│   ├── cli.py           # CLI entry point
│   ├── config.py        # Configuration
│   └── interactive.py   # Interactive mode
├── agents/              # AI agents (signal engine, backtester, LLM)
├── strategies/          # Strategy YAML specs
├── tests/               # 800+ pytest tests
├── docs/                # Documentation
├── finclaw.py           # Main entry point
└── pyproject.toml       # Package config
```

## Key Design Decisions

1. **Pure NumPy TA** — Zero dependency on TA-Lib; all indicators implemented in pure Python + NumPy for portability.

2. **Event-Driven Backtesting** — v3.6 added a full event-driven backtester alongside the vectorized one, enabling realistic order flow simulation.

3. **Plugin System** — Extensible via `register(manager)` pattern. Supports 4 plugin types without modifying core code.

4. **Layered Risk** — Position-level (stop-loss), strategy-level (Kelly), and portfolio-level (concentration limits, drawdown circuit breakers) risk management.

5. **Cache-First Data** — SQLite cache with configurable TTL reduces API calls and enables offline development.

6. **AGPL License** — Open source with copyleft to ensure community contributions flow back.
