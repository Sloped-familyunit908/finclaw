"""
Pre-built YAML strategy library — battle-tested templates ready to use.
"""

from __future__ import annotations

BUILTIN_STRATEGIES: dict[str, str] = {
    "golden-cross": """\
name: Golden Cross
description: Classic moving average crossover — buy when fast SMA crosses above slow SMA
universe: sp500
entry:
  - sma(20) > sma(50)
  - rsi(14) < 70
  - volume > sma_volume(20) * 1.5
exit:
  - sma(20) < sma(50)
  - OR: rsi(14) > 80
risk:
  stop_loss: 5%
  take_profit: 15%
  max_position: 10%
rebalance: weekly
""",

    "rsi-mean-reversion": """\
name: RSI Mean Reversion
description: Buy oversold, sell overbought — classic mean reversion on RSI
universe: sp500
entry:
  - rsi(14) < 30
  - close > sma(200)
exit:
  - rsi(14) > 70
  - OR: close < sma(200)
risk:
  stop_loss: 3%
  take_profit: 10%
  max_position: 5%
rebalance: daily
""",

    "breakout": """\
name: Breakout
description: Buy when price breaks above Bollinger upper band with volume confirmation
universe: sp500
entry:
  - close > bb_upper(20)
  - volume > sma_volume(20) * 2.0
  - adx(14) > 25
exit:
  - close < bb_middle(20)
  - OR: adx(14) < 20
risk:
  stop_loss: 4%
  take_profit: 12%
  max_position: 8%
rebalance: daily
""",

    "momentum": """\
name: Momentum
description: Trend-following with EMA stack and ADX filter
universe: sp500
entry:
  - ema(10) > ema(20)
  - ema(20) > ema(50)
  - adx(14) > 25
  - rsi(14) > 50
exit:
  - ema(10) < ema(20)
  - OR: rsi(14) < 40
risk:
  stop_loss: 5%
  take_profit: 20%
  max_position: 10%
rebalance: weekly
""",

    "value-investing": """\
name: Value Investing
description: Buy below long-term average with low RSI — patience pays
universe: sp500
entry:
  - close < sma(200)
  - rsi(14) < 40
exit:
  - close > sma(200) * 1.1
  - OR: rsi(14) > 75
risk:
  stop_loss: 8%
  take_profit: 25%
  max_position: 15%
rebalance: monthly
""",

    "dividend-aristocrat": """\
name: Dividend Aristocrat
description: Conservative entry on pullbacks with tight risk — buy quality on dips
universe: sp500
entry:
  - close < sma(50)
  - rsi(14) < 45
  - close > sma(200)
exit:
  - rsi(14) > 65
  - OR: close < sma(200)
risk:
  stop_loss: 3%
  take_profit: 10%
  max_position: 5%
rebalance: monthly
""",
}


def get_strategy(name: str) -> str:
    """Get a built-in strategy YAML by name."""
    if name not in BUILTIN_STRATEGIES:
        available = ", ".join(sorted(BUILTIN_STRATEGIES.keys()))
        raise KeyError(f"Unknown strategy '{name}'. Available: {available}")
    return BUILTIN_STRATEGIES[name]


def list_strategies() -> list[dict[str, str]]:
    """List all built-in strategies with name and description."""
    import yaml
    result = []
    for key, yaml_str in BUILTIN_STRATEGIES.items():
        config = yaml.safe_load(yaml_str)
        result.append({
            "id": key,
            "name": config.get("name", key),
            "description": config.get("description", ""),
            "rebalance": config.get("rebalance", "daily"),
        })
    return result
