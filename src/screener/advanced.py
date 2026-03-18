"""Advanced Stock Screener — multi-criteria filtering with exchange integration."""

from __future__ import annotations

import logging
import operator
from typing import Any, Callable

import numpy as np

from src.ta import rsi as calc_rsi, sma, atr, adx, bollinger_bands, obv

logger = logging.getLogger(__name__)


_OPS: dict[str, Callable] = {
    "<": operator.lt,
    ">": operator.gt,
    "<=": operator.le,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
}


class AdvancedScreener:
    """Screen stocks using flexible criteria against exchange data."""

    def __init__(self, exchange_registry=None):
        self._registry = exchange_registry
        self._field_calculators: dict[str, Callable] = {
            "rsi_14": self._calc_rsi_14,
            "volume_ratio": self._calc_volume_ratio,
            "price_change_5d": self._calc_price_change_5d,
            "price_change_1d": self._calc_price_change_1d,
            "price_change_20d": self._calc_price_change_20d,
            "atr_14": self._calc_atr_14,
            "adx_14": self._calc_adx_14,
            "bb_width": self._calc_bb_width,
            "sma_20": self._calc_sma_20,
            "sma_50": self._calc_sma_50,
            "above_sma_20": self._calc_above_sma_20,
            "above_sma_50": self._calc_above_sma_50,
            "52w_high_pct": self._calc_52w_high_pct,
            "52w_low_pct": self._calc_52w_low_pct,
        }

    # ------------------------------------------------------------------
    # Core screening
    # ------------------------------------------------------------------

    def screen(self, criteria: list[dict], universe: str = "sp500") -> list[dict]:
        """Screen a universe of symbols against criteria.

        Each criterion: {"field": "rsi_14", "op": "<", "value": 30}
        """
        symbols = self._resolve_universe(universe)
        results = []
        for sym in symbols:
            candles = self._fetch_candles(sym)
            if candles is None or len(candles) < 30:
                continue
            values = self._compute_fields(candles, sym)
            if self._matches(values, criteria):
                values["symbol"] = sym
                results.append(values)
        return results

    def top_movers(self, exchange: str, n: int = 20) -> list[dict]:
        """Return top *n* movers by absolute 1-day price change."""
        symbols = self._get_symbols_for_exchange(exchange)
        movers = []
        for sym in symbols:
            candles = self._fetch_candles(sym, exchange=exchange)
            if candles is None or len(candles) < 2:
                continue
            change = (candles[-1]["close"] - candles[-2]["close"]) / candles[-2]["close"]
            movers.append({"symbol": sym, "change_pct": change, "price": candles[-1]["close"]})
        movers.sort(key=lambda x: abs(x["change_pct"]), reverse=True)
        return movers[:n]

    def unusual_volume(self, exchange: str, threshold: float = 3.0) -> list[dict]:
        """Find symbols with volume >= *threshold* × 20-day average."""
        symbols = self._get_symbols_for_exchange(exchange)
        results = []
        for sym in symbols:
            candles = self._fetch_candles(sym, exchange=exchange, limit=30)
            if candles is None or len(candles) < 21:
                continue
            volumes = np.array([c["volume"] for c in candles], dtype=np.float64)
            avg_vol = np.mean(volumes[-21:-1])
            if avg_vol <= 0:
                continue
            ratio = volumes[-1] / avg_vol
            if ratio >= threshold:
                results.append({"symbol": sym, "volume_ratio": float(ratio), "volume": float(volumes[-1])})
        results.sort(key=lambda x: x["volume_ratio"], reverse=True)
        return results

    def new_highs_lows(self, exchange: str, period: int = 52) -> list[dict]:
        """Find symbols at *period*-week highs or lows."""
        symbols = self._get_symbols_for_exchange(exchange)
        days = period * 5  # approximate trading days
        results = []
        for sym in symbols:
            candles = self._fetch_candles(sym, exchange=exchange, limit=days + 5)
            if candles is None or len(candles) < days:
                continue
            highs = np.array([c["high"] for c in candles[-days:]], dtype=np.float64)
            lows = np.array([c["low"] for c in candles[-days:]], dtype=np.float64)
            current = candles[-1]["close"]
            if current >= np.max(highs):
                results.append({"symbol": sym, "type": "high", "price": current, "period_weeks": period})
            elif current <= np.min(lows):
                results.append({"symbol": sym, "type": "low", "price": current, "period_weeks": period})
        return results

    def sector_performance(self, period: str = "1w") -> dict[str, float]:
        """Return average performance by sector for the given period."""
        period_days = {"1d": 1, "1w": 5, "2w": 10, "1m": 21, "3m": 63, "6m": 126, "1y": 252}.get(period, 5)
        sector_map = self._get_sector_map()
        sector_returns: dict[str, list[float]] = {}
        for sym, sector in sector_map.items():
            candles = self._fetch_candles(sym, limit=period_days + 5)
            if candles is None or len(candles) < period_days + 1:
                continue
            ret = (candles[-1]["close"] - candles[-(period_days + 1)]["close"]) / candles[-(period_days + 1)]["close"]
            sector_returns.setdefault(sector, []).append(ret)
        return {s: float(np.mean(rets)) for s, rets in sector_returns.items() if rets}

    def correlation_scan(self, symbol: str, universe: list[str], period: int = 30) -> list[dict]:
        """Compute correlation of *symbol* with each ticker in *universe*."""
        base_candles = self._fetch_candles(symbol, limit=period + 5)
        if base_candles is None or len(base_candles) < period:
            return []
        base_prices = np.array([c["close"] for c in base_candles[-period:]], dtype=np.float64)
        base_returns = np.diff(base_prices) / base_prices[:-1]

        results = []
        for sym in universe:
            if sym == symbol:
                continue
            candles = self._fetch_candles(sym, limit=period + 5)
            if candles is None or len(candles) < period:
                continue
            prices = np.array([c["close"] for c in candles[-period:]], dtype=np.float64)
            returns = np.diff(prices) / prices[:-1]
            if len(returns) != len(base_returns):
                continue
            corr = float(np.corrcoef(base_returns, returns)[0, 1])
            results.append({"symbol": sym, "correlation": corr})
        results.sort(key=lambda x: abs(x["correlation"]), reverse=True)
        return results

    # ------------------------------------------------------------------
    # Field calculators
    # ------------------------------------------------------------------

    @staticmethod
    def _calc_rsi_14(candles: list[dict]) -> float | None:
        if len(candles) < 15:
            return None
        closes = np.array([c["close"] for c in candles], dtype=np.float64)
        vals = calc_rsi(closes, 14)
        return float(vals[-1]) if not np.isnan(vals[-1]) else None

    @staticmethod
    def _calc_volume_ratio(candles: list[dict]) -> float | None:
        if len(candles) < 21:
            return None
        volumes = np.array([c["volume"] for c in candles], dtype=np.float64)
        avg = np.mean(volumes[-21:-1])
        return float(volumes[-1] / avg) if avg > 0 else None

    @staticmethod
    def _calc_price_change(candles: list[dict], days: int) -> float | None:
        if len(candles) < days + 1:
            return None
        return (candles[-1]["close"] - candles[-(days + 1)]["close"]) / candles[-(days + 1)]["close"]

    @classmethod
    def _calc_price_change_1d(cls, candles):
        return cls._calc_price_change(candles, 1)

    @classmethod
    def _calc_price_change_5d(cls, candles):
        return cls._calc_price_change(candles, 5)

    @classmethod
    def _calc_price_change_20d(cls, candles):
        return cls._calc_price_change(candles, 20)

    @staticmethod
    def _calc_atr_14(candles: list[dict]) -> float | None:
        if len(candles) < 15:
            return None
        h = np.array([c["high"] for c in candles], dtype=np.float64)
        l = np.array([c["low"] for c in candles], dtype=np.float64)
        c = np.array([c["close"] for c in candles], dtype=np.float64)
        vals = atr(h, l, c, 14)
        return float(vals[-1]) if not np.isnan(vals[-1]) else None

    @staticmethod
    def _calc_adx_14(candles: list[dict]) -> float | None:
        if len(candles) < 28:
            return None
        h = np.array([c["high"] for c in candles], dtype=np.float64)
        l = np.array([c["low"] for c in candles], dtype=np.float64)
        c = np.array([c["close"] for c in candles], dtype=np.float64)
        vals = adx(h, l, c, 14)
        return float(vals[-1]) if not np.isnan(vals[-1]) else None

    @staticmethod
    def _calc_bb_width(candles: list[dict]) -> float | None:
        if len(candles) < 20:
            return None
        closes = np.array([c["close"] for c in candles], dtype=np.float64)
        bb = bollinger_bands(closes, 20, 2.0)
        upper, lower, mid = bb["upper"][-1], bb["lower"][-1], bb["middle"][-1]
        if mid == 0 or np.isnan(mid):
            return None
        return float((upper - lower) / mid)

    @staticmethod
    def _calc_sma_20(candles: list[dict]) -> float | None:
        if len(candles) < 20:
            return None
        closes = np.array([c["close"] for c in candles], dtype=np.float64)
        return float(sma(closes, 20)[-1])

    @staticmethod
    def _calc_sma_50(candles: list[dict]) -> float | None:
        if len(candles) < 50:
            return None
        closes = np.array([c["close"] for c in candles], dtype=np.float64)
        return float(sma(closes, 50)[-1])

    @staticmethod
    def _calc_above_sma_20(candles: list[dict]) -> bool | None:
        if len(candles) < 20:
            return None
        closes = np.array([c["close"] for c in candles], dtype=np.float64)
        s = sma(closes, 20)[-1]
        return bool(closes[-1] > s) if not np.isnan(s) else None

    @staticmethod
    def _calc_above_sma_50(candles: list[dict]) -> bool | None:
        if len(candles) < 50:
            return None
        closes = np.array([c["close"] for c in candles], dtype=np.float64)
        s = sma(closes, 50)[-1]
        return bool(closes[-1] > s) if not np.isnan(s) else None

    @staticmethod
    def _calc_52w_high_pct(candles: list[dict]) -> float | None:
        if len(candles) < 252:
            return None
        highs = np.array([c["high"] for c in candles[-252:]], dtype=np.float64)
        high_52w = np.max(highs)
        return float(candles[-1]["close"] / high_52w) if high_52w > 0 else None

    @staticmethod
    def _calc_52w_low_pct(candles: list[dict]) -> float | None:
        if len(candles) < 252:
            return None
        lows = np.array([c["low"] for c in candles[-252:]], dtype=np.float64)
        low_52w = np.min(lows)
        return float(candles[-1]["close"] / low_52w) if low_52w > 0 else None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_fields(self, candles: list[dict], symbol: str) -> dict:
        values: dict[str, Any] = {}
        for name, calc in self._field_calculators.items():
            try:
                val = calc(candles)
                if val is not None:
                    values[name] = val
            except Exception as e:
                logger.warning("Field '%s' computation failed for %s: %s", name, symbol, e)
        return values

    @staticmethod
    def _matches(values: dict, criteria: list[dict]) -> bool:
        for crit in criteria:
            field = crit.get("field", "")
            op_str = crit.get("op", ">")
            threshold = crit.get("value")
            if field not in values or threshold is None:
                return False
            op_fn = _OPS.get(op_str)
            if op_fn is None:
                return False
            if not op_fn(values[field], threshold):
                return False
        return True

    def _fetch_candles(self, symbol: str, exchange: str | None = None, limit: int = 300) -> list[dict] | None:
        if self._registry is None:
            return None
        try:
            adapter = self._registry.get(exchange or "yahoo")
            return adapter.get_ohlcv(symbol, timeframe="1d", limit=limit)
        except Exception:
            return None

    def _get_symbols_for_exchange(self, exchange: str) -> list[str]:
        if self._registry is None:
            return []
        try:
            adapter = self._registry.get(exchange)
            if hasattr(adapter, "list_symbols"):
                return adapter.list_symbols()
        except Exception as e:
            logger.warning("Failed to get symbols for exchange '%s': %s", exchange, e)
        return []

    def _resolve_universe(self, universe: str) -> list[str]:
        """Resolve a universe name to a list of symbols."""
        built_in = {
            "sp500": _SP500_SAMPLE,
            "nasdaq100": _NASDAQ100_SAMPLE,
            "dow30": _DOW30,
        }
        syms = built_in.get(universe.lower())
        if syms:
            return syms
        # Treat as comma-separated symbols
        return [s.strip().upper() for s in universe.split(",") if s.strip()]

    def _get_sector_map(self) -> dict[str, str]:
        """Return symbol -> sector mapping (sample)."""
        return {
            "AAPL": "Technology", "MSFT": "Technology", "GOOGL": "Technology",
            "AMZN": "Consumer Discretionary", "TSLA": "Consumer Discretionary",
            "JPM": "Financials", "BAC": "Financials", "GS": "Financials",
            "JNJ": "Healthcare", "UNH": "Healthcare", "PFE": "Healthcare",
            "XOM": "Energy", "CVX": "Energy",
            "PG": "Consumer Staples", "KO": "Consumer Staples",
        }


# Sample universes
_DOW30 = [
    "AAPL", "AMGN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "DOW",
    "GS", "HD", "HON", "IBM", "INTC", "JNJ", "JPM", "KO", "MCD", "MMM",
    "MRK", "MSFT", "NKE", "PG", "TRV", "UNH", "V", "VZ", "WBA", "WMT",
]

_SP500_SAMPLE = _DOW30 + [
    "GOOGL", "AMZN", "META", "TSLA", "NVDA", "BRK-B", "LLY", "AVGO", "XOM", "PEP",
    "COST", "ADBE", "NFLX", "AMD", "QCOM", "T", "LOW", "INTU", "AMAT", "BKNG",
]

_NASDAQ100_SAMPLE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO", "COST", "NFLX",
    "ADBE", "AMD", "QCOM", "INTU", "AMAT", "BKNG", "ISRG", "LRCX", "ADI", "KLAC",
]
