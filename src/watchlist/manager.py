"""Watchlist Manager - create, update, and query ticker watchlists.

Stores data in ~/.finclaw/watchlists.json with support for multiple named
watchlists, color-coded terminal display, and live quote fetching.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_PATH = Path.home() / ".finclaw" / "watchlists.json"


@dataclass
class WatchlistAlert:
    ticker: str
    condition: str  # e.g. "price > 200"
    triggered: bool = False
    message: str = ""


@dataclass
class Watchlist:
    name: str
    tickers: List[str] = field(default_factory=list)
    alerts: List[WatchlistAlert] = field(default_factory=list)


class WatchlistManager:
    """Manage multiple named watchlists, persisted as JSON."""

    def __init__(self, path: str | Path | None = None):
        self._path = Path(path) if path else DEFAULT_PATH
        self._lists: Dict[str, Watchlist] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                for name, data in raw.items():
                    alerts = [WatchlistAlert(**a) for a in data.get("alerts", [])]
                    self._lists[name] = Watchlist(
                        name=name,
                        tickers=data.get("tickers", []),
                        alerts=alerts,
                    )
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        for name, wl in self._lists.items():
            data[name] = {
                "tickers": wl.tickers,
                "alerts": [
                    {"ticker": a.ticker, "condition": a.condition,
                     "triggered": a.triggered, "message": a.message}
                    for a in wl.alerts
                ],
            }
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create(self, name: str, tickers: list | None = None) -> Watchlist:
        wl = Watchlist(name=name, tickers=[t.upper() for t in (tickers or [])])
        self._lists[name] = wl
        self._save()
        return wl

    def get(self, name: str) -> Optional[Watchlist]:
        return self._lists.get(name)

    def list_all(self) -> List[str]:
        return list(self._lists.keys())

    def add_ticker(self, name: str, ticker: str) -> None:
        wl = self._lists.get(name)
        if wl is None:
            raise KeyError(f"Watchlist '{name}' not found")
        t = ticker.upper()
        if t not in wl.tickers:
            wl.tickers.append(t)
            self._save()

    def add_tickers(self, name: str, tickers: list[str]) -> None:
        """Add multiple tickers at once."""
        wl = self._lists.get(name)
        if wl is None:
            raise KeyError(f"Watchlist '{name}' not found")
        for ticker in tickers:
            t = ticker.upper()
            if t not in wl.tickers:
                wl.tickers.append(t)
        self._save()

    def remove_ticker(self, name: str, ticker: str) -> None:
        wl = self._lists.get(name)
        if wl is None:
            raise KeyError(f"Watchlist '{name}' not found")
        t = ticker.upper()
        if t in wl.tickers:
            wl.tickers.remove(t)
            self._save()

    def add_alert(self, name: str, ticker: str, condition: str) -> None:
        wl = self._lists.get(name)
        if wl is None:
            raise KeyError(f"Watchlist '{name}' not found")
        wl.alerts.append(WatchlistAlert(ticker=ticker.upper(), condition=condition))
        self._save()

    def get_signals(self, name: str) -> List[Dict[str, Any]]:
        wl = self._lists.get(name)
        if wl is None:
            raise KeyError(f"Watchlist '{name}' not found")
        return [{"ticker": t, "signal": "neutral", "strength": 0.0} for t in wl.tickers]

    def get_alerts(self, name: str) -> List[WatchlistAlert]:
        wl = self._lists.get(name)
        if wl is None:
            raise KeyError(f"Watchlist '{name}' not found")
        return list(wl.alerts)

    def delete(self, name: str) -> bool:
        if name in self._lists:
            del self._lists[name]
            self._save()
            return True
        return False

    # ------------------------------------------------------------------
    # Quote fetching (for display)
    # ------------------------------------------------------------------

    def fetch_quotes(self, name: str) -> list[dict[str, Any]]:
        """Fetch live quotes for all tickers in a watchlist.

        Returns a list of dicts with keys:
          ticker, price, change, change_pct, volume, error
        """
        wl = self._lists.get(name)
        if wl is None:
            raise KeyError(f"Watchlist '{name}' not found")
        return [self._fetch_single(t) for t in wl.tickers]

    @staticmethod
    def _fetch_single(ticker: str) -> dict[str, Any]:
        """Fetch a single ticker quote via yfinance."""
        try:
            import yfinance as yf
            import warnings
            import logging
            logging.getLogger("yfinance").setLevel(logging.CRITICAL)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                t = yf.Ticker(ticker)
                hist = t.history(period="5d")
            if hist is None or len(hist) < 2:
                return {"ticker": ticker, "error": "no data"}
            price = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2])
            change = price - prev
            change_pct = change / prev if prev else 0
            volume = int(hist["Volume"].iloc[-1])
            return {
                "ticker": ticker,
                "price": price,
                "change": change,
                "change_pct": change_pct,
                "volume": volume,
                "error": None,
            }
        except Exception as e:
            return {"ticker": ticker, "error": str(e)}

    # ------------------------------------------------------------------
    # Formatted display
    # ------------------------------------------------------------------

    def format_table(self, name: str, quotes: list[dict] | None = None) -> str:
        """Return a color-coded terminal table for the watchlist."""
        wl = self._lists.get(name)
        if wl is None:
            raise KeyError(f"Watchlist '{name}' not found")
        if quotes is None:
            quotes = self.fetch_quotes(name)

        lines: list[str] = []
        lines.append(f"\n  Watchlist: {name} ({len(wl.tickers)} tickers)\n")
        lines.append(f"  {'Ticker':<10} {'Price':>10} {'Change':>10} {'%':>8} {'Volume':>14}")
        lines.append("  " + "-" * 56)

        for q in quotes:
            if q.get("error"):
                lines.append(f"  {q['ticker']:<10} {'error':>10} {q['error'][:30]}")
                continue
            price = q["price"]
            change = q["change"]
            pct = q["change_pct"]
            vol = q["volume"]

            # Color codes
            if change > 0:
                c_start, c_end = "\033[92m", "\033[0m"  # bright green
            elif change < 0:
                c_start, c_end = "\033[91m", "\033[0m"  # bright red
            else:
                c_start, c_end = "", ""

            lines.append(
                f"  {q['ticker']:<10} {price:>10.2f} "
                f"{c_start}{change:>+10.2f} {pct:>+7.2%}{c_end} "
                f"{vol:>14,}"
            )

        lines.append("")
        return "\n".join(lines)
