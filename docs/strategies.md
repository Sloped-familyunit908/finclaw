# Built-in Strategies

FinClaw ships with 10 built-in strategies defined as YAML configurations in `strategies/builtin/`. Each strategy specifies entry/exit rules, risk parameters, and optional AI agent confirmation.

---

## Strategy Overview

| Strategy | Difficulty | Assets | Timeframe | AI Agents |
|---|---|---|---|---|
| [Golden Cross Momentum](#golden-cross-momentum) | Beginner | BTC, ETH, SOL | 1d | value, momentum |
| [RSI Mean Reversion](#rsi-mean-reversion) | Beginner | BTC, ETH | 4h | momentum, sentiment |
| [Smart DCA](#smart-dca) | Beginner | BTC, ETH | 1d | value |
| [Bollinger Squeeze](#bollinger-squeeze) | Intermediate | BTC, ETH, SOL | 1d | quant |
| [Grid Trading](#grid-trading) | Intermediate | BTC, ETH | 1h | quant |
| [MACD Divergence](#macd-divergence) | Intermediate | BTC, ETH, SOL, AVAX, LINK | 1d | quant |
| [Multi-Timeframe Trend](#multi-timeframe-trend) | Advanced | BTC, ETH | 1d + 1w | value, quant, macro |
| [Volume Profile Breakout](#volume-profile-breakout) | Advanced | BTC, ETH, SOL | 4h | quant, macro |
| [AI Sentiment Reversal](#ai-sentiment-reversal) | Expert | BTC | 1d | value, quant, macro, sentiment |
| [Strategy Combiner](#strategy-combiner) | Advanced | Any | Any | Configurable |

---

## Golden Cross Momentum

Classic SMA50/SMA200 golden cross enhanced with AI confirmation.

**Entry:** SMA50 crosses above SMA200 + RSI between 30-70 + AI confidence ≥ 0.6

**Exit:** Take profit 15%, stop loss 5%, trailing stop 3%, max hold 30 days

**Parameters:**

| Parameter | Value | Description |
|---|---|---|
| `fast` | 50 | Fast SMA period |
| `slow` | 200 | Slow SMA period |
| `rsi_period` | 14 | RSI calculation period |
| `ai_min_confidence` | 0.6 | Minimum AI debate confidence |
| `max_positions` | 3 | Maximum concurrent positions |
| `max_position_pct` | 0.20 | Max 20% capital per position |

```bash
python finclaw.py backtest --strategy golden_cross --ticker BTC-USD --start 2023-01-01
```

---

## RSI Mean Reversion

Buy oversold (RSI < 30), sell overbought (RSI > 70). AI sentiment prevents buying into real crashes.

**Entry:** RSI below 30 + price below lower Bollinger Band + AI confidence ≥ 0.5

**Exit:** Take profit 8%, stop loss 4%, trailing stop 2%, max hold 14 days

**Parameters:**

| Parameter | Value |
|---|---|
| `rsi_period` | 14 |
| `bollinger_period` | 20 |
| `max_position_pct` | 0.15 |
| `max_drawdown_pct` | 0.10 |

---

## Smart DCA

Enhanced Dollar-Cost Averaging that buys more when price is lower. Uses RSI to dynamically adjust buy size.

**Schedule:** Weekly (Monday)

**Position Sizing Multipliers:**

| Condition | Multiplier |
|---|---|
| RSI < 30 (extreme fear) | 2.0x |
| RSI < 40 (fear) | 1.5x |
| RSI > 70 (greed) | 0.5x |
| RSI > 80 (extreme greed) | 0.25x |
| Price < SMA200 | 1.5x |

**Base amount:** $100/week (configurable)

---

## Bollinger Squeeze

Detects low-volatility squeezes and trades the breakout. Buys when price breaks above the upper band after bandwidth contracts.

**Entry:** Bandwidth below 20-day average (squeeze) + price crosses above upper band + volume > 1.5× average

**Exit:** Take profit 8%, stop loss 3%, trailing stop 4%, or price crosses below middle band

---

## Grid Trading

Automated grid trading for range-bound markets. Places buy/sell orders at fixed price intervals.

**Parameters:**

| Parameter | Value | Description |
|---|---|---|
| `grid_levels` | 10 | Number of grid levels |
| `grid_spacing_pct` | 0.02 | 2% between levels |
| `order_size_pct` | 0.10 | 10% capital per grid order |
| `range_type` | arithmetic | arithmetic or geometric |
| `upper_bound_pct` | 0.10 | Grid ceiling (10% above center) |
| `lower_bound_pct` | -0.10 | Grid floor (10% below center) |

**Safety:** Emergency stop at -15% total loss. Auto-exits if price breaks outside grid range.

---

## MACD Divergence

Detects bullish/bearish divergence between price and MACD histogram — one of the most reliable reversal signals.

**Bullish Entry:** Price makes lower low + MACD histogram makes higher low + MACD bullish signal cross

**Bearish Entry:** Price makes higher high + MACD histogram makes lower high

**MACD Settings:** Fast 12, Slow 26, Signal 9

---

## Multi-Timeframe Trend

Professional-grade trend following used by CTAs. Uses weekly EMA for direction, daily EMA crossover for entry timing.

**Long Entry:** Weekly trend bullish + daily EMA21 crosses above EMA55 + ADX > 25 + RSI 40-70

**Short Entry:** Weekly trend bearish + daily death cross + ADX > 25

**Requires:** AI debate confidence ≥ 0.60

---

## Volume Profile Breakout

Inspired by TPO/Market Profile. Trades breakouts from high-volume price levels (Value Area).

**Entry:** Price crosses above VWAP + volume > 2× average + On-Balance Volume trend bullish

**Exit:** Take profit 10%, stop loss 3%, trailing stop 5%, or price crosses below VWAP

---

## AI Sentiment Reversal

Expert-level strategy using AI agents to gauge market sentiment via the Fear & Greed Index. Trades reversals at sentiment extremes.

**Agents:** value, quant, macro, sentiment (2 debate rounds, min confidence 0.65)

**Buy Signal:** Fear & Greed < 20 + RSI < 35 + AI consensus = BUY

**Sell Signal:** Fear & Greed > 80 + RSI > 70 + AI consensus = SELL

**Risk:** Max 15% position, 3-tranche scaling (add more on 3% and 6% dips)

---

## Strategy Combiner

Weighted ensemble that combines signals from multiple strategies with regime detection.

```python
from src.strategies.combiner import StrategyCombiner

combiner = StrategyCombiner(
    strategies=["momentum_jt", "mean_reversion", "trend_following"],
    weights=[0.4, 0.3, 0.3],
    regime_aware=True,
)
signal = combiner.generate_signal(data)
```

The combiner automatically adjusts weights based on detected market regime (bull/bear/sideways).

---

## CLI Strategy Presets

The CLI offers 10 named presets for quick scans (see [CLI Reference](cli-reference.md)):

| Preset | Description |
|---|---|
| `druckenmiller` | Top-3 momentum, max conviction |
| `soros` | AI narrative + momentum |
| `lynch` | High growth/volatility ratio |
| `buffett` | Quality + dip recovery |
| `dalio` | All-weather risk parity |
| `momentum` | Top-5 momentum score |
| `mean_reversion` | Buy-the-dip plays |
| `aggressive` | Top-5 walk-forward return |
| `balanced` | Top-10 grade-weighted |
| `conservative` | Top-15 low-volatility |

---

## Custom Strategies

See [Plugins → Strategy Plugins](plugins.md#strategy-plugins) for creating your own.
