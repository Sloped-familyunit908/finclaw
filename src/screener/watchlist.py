"""Enhanced Watchlist Manager — create, manage, and query watchlists with quotes and export."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Watchlist:
    """A named collection of ticker symbols."""
    name: str
    symbols: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class WatchlistManager:
    """Manage named watchlists with persistence, quotes, and import/export."""

    def __init__(self, path: str = "watchlists.json", exchange_registry=None):
        self._path = Path(path)
        self._registry = exchange_registry
        self._lists: Dict[str, Watchlist] = {}
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                for name, data in raw.items():
                    self._lists[name] = Watchlist(
                        name=name,
                        symbols=data.get("symbols", data.get("tickers", [])),
                        metadata=data.get("metadata", {}),
                    )
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        for name, wl in self._lists.items():
            data[name] = {"symbols": wl.symbols, "metadata": wl.metadata}
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(self, name: str, symbols: list[str] | None = None) -> Watchlist:
        """Create a new watchlist."""
        wl = Watchlist(name=name, symbols=[s.upper() for s in (symbols or [])])
        self._lists[name] = wl
        self._save()
        return wl

    def add(self, name: str, symbol: str) -> None:
        """Add a symbol to an existing watchlist."""
        wl = self._get_or_raise(name)
        s = symbol.upper()
        if s not in wl.symbols:
            wl.symbols.append(s)
            self._save()

    def remove(self, name: str, symbol: str) -> None:
        """Remove a symbol from a watchlist."""
        wl = self._get_or_raise(name)
        s = symbol.upper()
        if s in wl.symbols:
            wl.symbols.remove(s)
            self._save()

    def get(self, name: str) -> Watchlist | None:
        return self._lists.get(name)

    def list_all(self) -> list[str]:
        return list(self._lists.keys())

    def delete(self, name: str) -> bool:
        if name in self._lists:
            del self._lists[name]
            self._save()
            return True
        return False

    # ------------------------------------------------------------------
    # Quotes
    # ------------------------------------------------------------------

    def get_quotes(self, name: str) -> list[dict]:
        """Fetch latest quotes for all symbols in a watchlist."""
        wl = self._get_or_raise(name)
        quotes = []
        for sym in wl.symbols:
            quote = self._fetch_quote(sym)
            if quote:
                quotes.append(quote)
            else:
                quotes.append({"symbol": sym, "error": "unavailable"})
        return quotes

    # ------------------------------------------------------------------
    # Export / Import
    # ------------------------------------------------------------------

    def export(self, name: str, format: str = "csv") -> str:
        """Export watchlist to string (csv or json)."""
        wl = self._get_or_raise(name)
        if format == "json":
            return json.dumps({"name": wl.name, "symbols": wl.symbols}, indent=2)
        # CSV
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["symbol"])
        for s in wl.symbols:
            writer.writerow([s])
        return buf.getvalue()

    def import_from(self, filepath: str) -> Watchlist:
        """Import a watchlist from a CSV or JSON file."""
        p = Path(filepath)
        content = p.read_text(encoding="utf-8")
        if p.suffix == ".json":
            data = json.loads(content)
            name = data.get("name", p.stem)
            symbols = data.get("symbols", [])
        else:
            # CSV
            reader = csv.DictReader(io.StringIO(content))
            symbols = []
            for row in reader:
                sym = row.get("symbol") or row.get("ticker") or ""
                if sym.strip():
                    symbols.append(sym.strip().upper())
            name = p.stem
        return self.create(name, symbols)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_or_raise(self, name: str) -> Watchlist:
        wl = self._lists.get(name)
        if wl is None:
            raise KeyError(f"Watchlist '{name}' not found")
        return wl

    def _fetch_quote(self, symbol: str) -> dict | None:
        if self._registry is None:
            return {"symbol": symbol, "last": None, "source": "no_exchange"}
        try:
            adapter = self._registry.get("yahoo")
            return adapter.get_ticker(symbol)
        except Exception:
            return None
