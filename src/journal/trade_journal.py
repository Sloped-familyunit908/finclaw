"""Trade Journal — log, query, and analyze trades."""

from __future__ import annotations

import csv
import io
import json
import datetime
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Trade:
    ticker: str
    side: str  # "buy" | "sell"
    quantity: float
    price: float
    date: str  # ISO date string
    pnl: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class JournalEntry:
    trade: Trade
    notes: str = ""
    tags: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.datetime.now().isoformat())


class TradeJournal:
    """Persistent trade journal backed by a JSON file."""

    def __init__(self, path: str = "trade_journal.json"):
        self._path = Path(path)
        self._entries: List[JournalEntry] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self._path.exists():
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            for item in raw:
                t = Trade(**item["trade"])
                self._entries.append(JournalEntry(
                    trade=t,
                    notes=item.get("notes", ""),
                    tags=item.get("tags", []),
                    timestamp=item.get("timestamp", ""),
                ))

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = []
        for e in self._entries:
            data.append({
                "trade": e.trade.to_dict(),
                "notes": e.notes,
                "tags": e.tags,
                "timestamp": e.timestamp,
            })
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_trade(self, trade: Trade, notes: str = "", tags: list = None) -> JournalEntry:
        entry = JournalEntry(trade=trade, notes=notes, tags=tags or [])
        self._entries.append(entry)
        self._save()
        return entry

    def get_trades(
        self,
        ticker: str = None,
        date_range: tuple = None,
        tags: list = None,
    ) -> List[JournalEntry]:
        results = self._entries
        if ticker:
            results = [e for e in results if e.trade.ticker.upper() == ticker.upper()]
        if date_range:
            start, end = str(date_range[0]), str(date_range[1])
            results = [e for e in results if start <= e.trade.date <= end]
        if tags:
            tag_set = set(tags)
            results = [e for e in results if tag_set & set(e.tags)]
        return results

    def analyze(self) -> Dict[str, Any]:
        """Return win-rate, avg win/loss, best/worst trade, total PnL."""
        if not self._entries:
            return {"total_trades": 0}
        pnls = [e.trade.pnl for e in self._entries]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        return {
            "total_trades": len(pnls),
            "win_rate": len(wins) / len(pnls) if pnls else 0,
            "avg_win": sum(wins) / len(wins) if wins else 0,
            "avg_loss": sum(losses) / len(losses) if losses else 0,
            "best_trade": max(pnls),
            "worst_trade": min(pnls),
            "total_pnl": sum(pnls),
        }

    def export(self, format: str = "csv") -> str:
        """Export journal. Returns string content (CSV or JSON)."""
        if format == "json":
            return json.dumps(
                [{"trade": e.trade.to_dict(), "notes": e.notes, "tags": e.tags, "timestamp": e.timestamp}
                 for e in self._entries], indent=2)
        # CSV
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["date", "ticker", "side", "qty", "price", "pnl", "notes", "tags"])
        for e in self._entries:
            t = e.trade
            writer.writerow([t.date, t.ticker, t.side, t.quantity, t.price, t.pnl, e.notes, ";".join(e.tags)])
        return buf.getvalue()
