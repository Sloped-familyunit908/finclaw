# DeFi Monitoring

FinClaw includes DeFi yield tracking, on-chain analytics, and funding rate arbitrage tools.

---

## On-Chain Analytics

### Whale Tracking

Monitor large wallet movements:

```python
from src.crypto.onchain import WhaleTracker

tracker = WhaleTracker()
movements = tracker.get_large_transfers("BTC", min_amount_usd=1_000_000)
for tx in movements:
    print(f"{tx['from']} → {tx['to']}: {tx['amount_btc']} BTC (${tx['amount_usd']:,.0f})")
```

### Flow Analysis

Track exchange inflows/outflows as a sentiment signal:

```python
flows = tracker.get_exchange_flows("ETH", period="7d")
print(f"Net flow: {flows['net_flow']:.2f} ETH")
# Positive = deposits (bearish), Negative = withdrawals (bullish)
```

---

## DeFi Yield Tracking

Monitor yields across DeFi protocols:

```python
from src.defi.yield_tracker import DeFiYieldTracker

yields = DeFiYieldTracker()
top_yields = yields.get_top_yields(min_tvl=1_000_000, limit=20)

for pool in top_yields:
    print(f"{pool['protocol']} - {pool['pair']}: {pool['apy']:.1f}% APY (TVL: ${pool['tvl']:,.0f})")
```

### Yield Alerts

```python
yields.set_alert(
    protocol="aave",
    pool="USDC",
    condition="apy_above",
    threshold=8.0,
    webhook="https://hooks.slack.com/...",
)
```

---

## Crypto Rebalancer

Automated portfolio rebalancing for crypto holdings:

```python
from src.crypto.rebalancer import CryptoRebalancer

rebalancer = CryptoRebalancer(
    target_weights={"BTC": 0.50, "ETH": 0.30, "SOL": 0.20},
    rebalance_threshold=0.05,  # Rebalance when 5% off target
)

trades = rebalancer.calculate_rebalance(current_holdings)
for trade in trades:
    print(f"{trade['action']} {trade['amount']:.4f} {trade['symbol']}")
```

---

## Funding Rate Arbitrage

Exploit funding rate differences between exchanges:

```python
from src.crypto.arbitrage import FundingArbScanner

scanner = FundingArbScanner(exchanges=["binance", "bybit", "okx"])
opportunities = scanner.scan(symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"])

for opp in opportunities:
    print(f"{opp['symbol']}: {opp['long_exchange']} ({opp['long_rate']:.4%}) vs "
          f"{opp['short_exchange']} ({opp['short_rate']:.4%}) = "
          f"{opp['spread']:.4%} annualized")
```

### How Funding Arb Works

1. **Identify spread** — Find pairs where funding rates differ significantly between exchanges
2. **Go long on negative** — Buy perpetual on the exchange paying you funding
3. **Go short on positive** — Sell perpetual on the exchange where you pay less
4. **Collect the spread** — Funding payments settle every 8 hours

---

## Built-in Crypto Strategies

### Grid Trading

See [Strategies → Grid Trading](strategies.md#grid-trading)

### Smart DCA

See [Strategies → Smart DCA](strategies.md#smart-dca)

### Cross-Exchange Arbitrage

```python
from src.strategies.crypto_strategies import CryptoArbitrageStrategy

arb = CryptoArbitrageStrategy(
    exchanges=["binance", "bybit"],
    symbols=["BTCUSDT"],
    min_spread_pct=0.003,  # 0.3% minimum spread
)
arb.start()
```

---

## MCP Integration

All DeFi tools are available via MCP:

- `get_funding_rates` — Current funding rates for crypto perpetuals
- `get_quote` with crypto exchanges — Real-time crypto prices
- `run_backtest` with crypto strategies — Backtest grid/DCA/arb strategies
