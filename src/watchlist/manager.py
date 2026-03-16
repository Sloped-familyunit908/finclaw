"""Watchlist Manager — create, update, and query ticker watchlists."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


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

    def __init__(self, path: str = "watchlists.json"):
        self._path = Path(path)
        self._lists: Dict[str, Watchlist] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            for name, data in raw.items():
                alerts = [WatchlistAlert(**a) for a in data.get("alerts", [])]
                self._lists[name] = Watchlist(name=name, tickers=data.get("tickers", []), alerts=alerts)

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        for name, wl in self._lists.items():
            data[name] = {
                "tickers": wl.tickers,
                "alerts": [{"ticker": a.ticker, "condition": a.condition, "triggered": a.triggered, "message": a.message} for a in wl.alerts],
            }
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create(self, name: str, tickers: list = None) -> Watchlist:
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
        """Return simple signal placeholders for each ticker (extensible hook)."""
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
