# FinClaw Ecosystem — Build & Contribute Guide

## How the Ecosystem Works

FinClaw is designed around an **open ecosystem** where anyone can contribute:

```
┌──────────────────────────────────────────────────────────────┐
│                    FinClaw Ecosystem                     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Strategy     │  │  Agent       │  │  Data        │       │
│  │  Marketplace  │  │  Plugins     │  │  Connectors  │       │
│  │              │  │              │  │              │       │
│  │  YAML-based  │  │  Python pkg  │  │  Rust crate  │       │
│  │  Anyone can  │  │  Custom AI   │  │  New data    │       │
│  │  contribute  │  │  personalities│  │  sources     │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                 │                 │               │
│         └─────────────────┼─────────────────┘               │
│                           │                                  │
│              ┌────────────▼────────────┐                     │
│              │    FinClaw Core     │                     │
│              │   Rust Engine + Python  │                     │
│              └────────────┬────────────┘                     │
│                           │                                  │
│              ┌────────────▼────────────┐                     │
│              │   Leaderboard & Social  │                     │
│              │   Rankings, Follow,     │                     │
│              │   Strategy Battles      │                     │
│              └─────────────────────────┘                     │
└──────────────────────────────────────────────────────────────┘
```

## 3 Ways to Contribute

### 1. Contribute a Strategy (Easiest — No Coding!)

Add a YAML file to `strategies/community/`:

```yaml
# strategies/community/your-strategy.yaml
apiVersion: whale/v1
kind: Strategy
metadata:
  name: my-awesome-strategy
  version: 1.0.0
  author: your-github-username
  description: My strategy description
  tags: [crypto, momentum]
spec:
  assets:
    type: crypto
    symbols: [BTC, ETH]
  timeframe: 4h
  agents: [value, quant]
  entry:
    rules:
      - indicator: rsi
        period: 14
        condition: below
        threshold: 30
  exit:
    take_profit: 0.10
    stop_loss: 0.05
  risk:
    max_position_pct: 0.20
```

Submit a PR → Automated backtest runs → Results added → Merged!

### 2. Create an Agent Plugin (Python)

Build a custom AI personality:

```python
# agents/plugins/contrarian.py
from agents.registry import AgentProfile

MY_AGENT = AgentProfile(
    name="Contrarian Carl",
    role="Contrarian Trader",
    avatar="🔄",
    color="#FF6B35",
    system_prompt="""You are a contrarian trader.
    When everyone is bullish, you look for sells.
    When everyone is bearish, you look for buys.
    ..."""
)
```

Register it:
```python
# agents/plugins/__init__.py
from .contrarian import MY_AGENT
register_agent("contrarian", MY_AGENT)
```

### 3. Add a Data Connector (Rust)

Implement the `DataSource` trait:

```rust
// engine/src/data/sources/my_source.rs
use async_trait::async_trait;

#[async_trait]
impl DataSource for MySource {
    async fn get_price(&self, symbol: &str) -> Result<f64>;
    async fn get_history(&self, symbol: &str, days: u32) -> Result<Vec<Bar>>;
}
```

## Governance

### RFC Process (Request for Comments)
Major changes go through an RFC:
1. Open a GitHub Discussion with the `[RFC]` prefix
2. Community debates for 7 days
3. Core team makes final decision
4. Implementation begins

### Versioning
- Core engine: Semantic versioning (1.0.0)
- Strategies: Independent versioning per strategy
- API: Backwards compatible within major versions

### Strategy Quality Tiers
- ⭐ **Community** — Any PR, basic validation
- ⭐⭐ **Verified** — Backtested, reviewed by maintainers
- ⭐⭐⭐ **Certified** — Live-tested, consistent performance

## Bounty Program

We'll launch a bounty program for high-impact contributions:
- New exchange connector: $200-500
- Top-performing strategy (monthly): $100
- Security vulnerability: $500-2000
- Documentation improvement: $50

## How to Build Your Reputation

1. **Contribute strategies** → Get listed on the leaderboard
2. **Write agents** → Your AI personality used by thousands
3. **Fix bugs** → Become a core contributor
4. **Write docs** → Help grow the community
5. **Give talks** → We'll support your conference proposals

## Comparable Ecosystems We're Learning From

| Project | Ecosystem Model | What We Take |
|---------|----------------|--------------|
| OpenClaw | Skills + Plugins | Agent plugin architecture |
| Kubernetes | Operators + CRDs | YAML-based configuration |
| Terraform | Providers | Data source plugins |
| HuggingFace | Model Hub | Strategy marketplace |
| Home Assistant | Integrations | Community contribution model |
| VS Code | Extensions | Plugin discovery + install |

## Naming: "FinClaw" → Think "whale" = Big Player

The whale metaphor works:
- 🐋 Whale = Smart money, institutional-grade
- 📦 Pod = A group of strategies (like Kubernetes pods)
- 🌊 Stream = Real-time data flow
- 🏟️ Arena = Where agents debate

CLI commands:
```bash
whale pod list          # List installed strategy pods
whale pod install <n>   # Install a strategy pod
whale pod run <n>       # Run a strategy pod
whale arena watch       # Watch live agent debates
whale stream prices     # Stream real-time prices
whale backtest <n>      # Backtest a strategy
```
