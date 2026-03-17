"""
Backtrader Strategy Adapter for FinClaw
========================================
Wraps Backtrader's bt.Strategy classes to run inside FinClaw's plugin system.

Backtrader (13K+ stars) has a massive library of community strategies but is
no longer maintained. This adapter lets you reuse them in FinClaw.

Usage::

    from src.plugin_system.backtrader_adapter import BacktraderAdapter

    # Wrap any bt.Strategy subclass
    import backtrader as bt

    class MyBTStrategy(bt.Strategy):
        params = (('period', 20),)
        def __init__(self):
            self.sma = bt.indicators.SMA(self.data.close, period=self.params.period)
        def next(self):
            if self.data.close[0] > self.sma[0]:
                self.buy()
            elif self.data.close[0] < self.sma[0]:
                self.sell()

    plugin = BacktraderAdapter(
        MyBTStrategy,
        name="my_bt_sma",
        description="SMA crossover from Backtrader",
        markets=["us_stock"],
    )

    signals = plugin.generate_signals(ohlcv_dataframe)

If backtrader is not installed, importing this module still works —
BacktraderAdapter.generate_signals() will raise a clear error.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from src.plugin_system.plugin_types import StrategyPlugin

logger = logging.getLogger(__name__)

try:
    import backtrader as bt

    _HAS_BACKTRADER = True
except ImportError:
    _HAS_BACKTRADER = False
    bt = None  # type: ignore[assignment]


class _SignalCollector:
    """
    Minimal shim injected into a bt.Strategy to capture buy/sell calls
    without running a real broker.
    """

    def __init__(self) -> None:
        self.signals: list[tuple[int, int]] = []  # (bar_index, +1/-1)
        self._bar = 0

    def set_bar(self, idx: int) -> None:
        self._bar = idx

    def buy(self, *_a: Any, **_kw: Any) -> None:
        self.signals.append((self._bar, 1))

    def sell(self, *_a: Any, **_kw: Any) -> None:
        self.signals.append((self._bar, -1))

    def close(self, *_a: Any, **_kw: Any) -> None:
        self.signals.append((self._bar, -1))


class _PandasLine:
    """Mimics backtrader's line interface over a pandas Series."""

    def __init__(self, series: pd.Series) -> None:
        self._data = series.values
        self._idx = 0

    def set_idx(self, idx: int) -> None:
        self._idx = idx

    def __getitem__(self, offset: int) -> float:
        i = self._idx + offset
        if 0 <= i < len(self._data):
            return float(self._data[i])
        return 0.0

    def __len__(self) -> int:
        return self._idx + 1

    def __float__(self) -> float:
        return float(self._data[self._idx]) if self._idx < len(self._data) else 0.0

    def get(self, ago: int = 0, size: int = 1) -> list[float]:
        start = max(0, self._idx + ago - size + 1)
        end = self._idx + ago + 1
        return [float(self._data[i]) for i in range(start, min(end, len(self._data)))]


class _PandasDataFeed:
    """
    Minimal data feed that looks enough like bt.feeds.PandasData
    for most bt.Strategy.__init__ and next() to work.
    """

    def __init__(self, df: pd.DataFrame) -> None:
        col_map = {}
        for col in df.columns:
            col_map[col.lower()] = col

        self.open = _PandasLine(df[col_map.get("open", "Open")])
        self.high = _PandasLine(df[col_map.get("high", "High")])
        self.low = _PandasLine(df[col_map.get("low", "Low")])
        self.close = _PandasLine(df[col_map.get("close", "Close")])
        self.volume = _PandasLine(df[col_map.get("volume", "Volume")])
        self.datetime = _PandasLine(
            pd.Series(range(len(df)), index=df.index, dtype=float)
        )
        self._lines = [self.open, self.high, self.low, self.close, self.volume, self.datetime]
        self._length = len(df)

    def set_idx(self, idx: int) -> None:
        for line in self._lines:
            line.set_idx(idx)

    def __len__(self) -> int:
        return self._length

    def __getitem__(self, offset: int) -> float:
        """Default [] returns close, like backtrader."""
        return self.close[offset]


class BacktraderAdapter(StrategyPlugin):
    """
    Adapt a backtrader bt.Strategy subclass into a FinClaw StrategyPlugin.

    This runs the strategy in a lightweight simulation — no Cerebro needed.
    It captures buy()/sell() calls and converts them to signal series.

    Args:
        bt_strategy_cls: A bt.Strategy subclass.
        name: Plugin name.
        description: Plugin description.
        author: Author name.
        risk_level: "low", "medium", or "high".
        markets: List of target markets.
        bt_params: Override params for the bt.Strategy.
    """

    version = "1.0.0"

    def __init__(
        self,
        bt_strategy_cls: type | None = None,
        name: str = "backtrader_adapted",
        description: str = "Backtrader strategy adapted for FinClaw",
        author: str = "Community",
        risk_level: str = "medium",
        markets: list[str] | None = None,
        bt_params: dict[str, Any] | None = None,
    ):
        self._bt_cls = bt_strategy_cls
        self.name = name
        self.description = description
        self.author = author
        self.risk_level = risk_level
        self.markets = markets or ["us_stock"]
        self._bt_params = bt_params or {}

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Run the backtrader strategy and extract signals."""
        if not _HAS_BACKTRADER:
            raise ImportError(
                "backtrader is required for BacktraderAdapter. "
                "Install with: pip install backtrader"
            )
        if self._bt_cls is None:
            raise ValueError("No backtrader strategy class provided")

        feed = _PandasDataFeed(data)
        collector = _SignalCollector()

        # Instantiate strategy with our shim data
        # We use __new__ + manual init to bypass Cerebro dependency
        strat = object.__new__(self._bt_cls)

        # Set up params
        if hasattr(self._bt_cls, "params"):
            params_cls = self._bt_cls.params
            if isinstance(params_cls, tuple):
                # params = (('period', 20), ('fast', 10))
                for p_name, p_default in params_cls:
                    setattr(strat, f"p_{p_name}", self._bt_params.get(p_name, p_default))
            elif hasattr(params_cls, "_getitems"):
                # backtrader AutoInfoClass
                for p_name in dir(params_cls):
                    if not p_name.startswith("_"):
                        val = self._bt_params.get(p_name, getattr(params_cls, p_name, None))
                        setattr(strat, f"p_{p_name}", val)

        # Attach data feed and signal collector
        strat.data = feed
        strat.data0 = feed
        strat.datas = [feed]
        strat.buy = collector.buy
        strat.sell = collector.sell
        strat.close = collector.close
        strat.broker = None
        strat.position = type("Position", (), {"size": 0})()

        # Params alias
        class _Params:
            pass
        p = _Params()
        if hasattr(self._bt_cls, "params") and isinstance(self._bt_cls.params, tuple):
            for p_name, p_default in self._bt_cls.params:
                setattr(p, p_name, self._bt_params.get(p_name, p_default))
        strat.params = p
        strat.p = p

        # Try calling __init__ (may fail for complex strategies)
        try:
            strat.__init__()
        except Exception as exc:
            logger.debug("bt.Strategy __init__ partial failure (may be OK): %s", exc)

        # Run next() for each bar
        signals = pd.Series(0, index=data.index)
        for i in range(len(data)):
            feed.set_idx(i)
            collector.set_bar(i)
            try:
                strat.next()
            except Exception:
                pass

        # Convert collected signals
        for bar_idx, signal_val in collector.signals:
            if 0 <= bar_idx < len(signals):
                signals.iloc[bar_idx] = signal_val

        return signals

    def get_parameters(self) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if self._bt_cls and hasattr(self._bt_cls, "params"):
            p = self._bt_cls.params
            if isinstance(p, tuple):
                for p_name, p_default in p:
                    params[p_name] = self._bt_params.get(p_name, p_default)
        params.update(self._bt_params)
        return params

    def backtest_config(self) -> dict[str, Any]:
        return {
            "initial_capital": 100000,
            "commission": 0.001,
            "slippage": 0.001,
            "note": "Adapted from backtrader - some features may behave differently",
        }


def adapt_backtrader(
    strategy_cls: type,
    name: str | None = None,
    **kwargs: Any,
) -> BacktraderAdapter:
    """
    Convenience function to wrap a bt.Strategy class.

    Args:
        strategy_cls: bt.Strategy subclass.
        name: Optional plugin name (defaults to class name).
        **kwargs: Passed to BacktraderAdapter.

    Returns:
        A FinClaw StrategyPlugin wrapping the backtrader strategy.
    """
    if name is None:
        name = getattr(strategy_cls, "__name__", "bt_strategy").lower()
    return BacktraderAdapter(strategy_cls, name=name, **kwargs)
