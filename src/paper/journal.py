"""
Trade Journal - record, annotate, and review paper trades.
"""

from __future__ import annotations

import csv
import io
import json
import os
from datetime import datetime, timedelta
from typing import Any


class TradeJournal:
    """Journal for recording trades with notes and generating summaries."""

    def __init__(self, journal_path: str | None = None):
        self.journal_path = journal_path
        self._entries: list[dict] = []
        self._notes: list[dict] = []
        if journal_path and os.path.exists(journal_path):
            self._load()

    def record_trade(self, trade: dict, reason: str = "") -> None:
        """Record a trade with optional reason."""
        entry = {
            "type": "trade",
            "timestamp": trade.get("timestamp", datetime.now().timestamp()),
            "symbol": trade.get("symbol", ""),
            "side": trade.get("side", ""),
            "quantity": trade.get("quantity", 0),
            "price": trade.get("price", 0),
            "reason": reason,
            "pnl": trade.get("pnl", None),
        }
        self._entries.append(entry)
        self._save()

    def add_note(self, text: str) -> None:
        """Add a journal note."""
        note = {
            "type": "note",
            "timestamp": datetime.now().timestamp(),
            "text": text,
        }
        self._notes.append(note)
        self._save()

    def daily_summary(self, date: str | None = None) -> str:
        """Generate a summary for a given date (YYYY-MM-DD) or today."""
        if date:
            target = datetime.strptime(date, "%Y-%m-%d").date()
        else:
            target = datetime.now().date()

        day_trades = [
            e for e in self._entries
            if e["type"] == "trade"
            and datetime.fromtimestamp(e["timestamp"]).date() == target
        ]
        day_notes = [
            n for n in self._notes
            if datetime.fromtimestamp(n["timestamp"]).date() == target
        ]

        lines: list[str] = []
        lines.append(f"📅 Daily Summary: {target.isoformat()}")
        lines.append(f"Trades: {len(day_trades)}")

        total_pnl = 0.0
        for t in day_trades:
            side = t["side"]
            lines.append(f"  {side} {t['symbol']} x{t['quantity']} @${t['price']:.2f}")
            if t.get("reason"):
                lines.append(f"    Reason: {t['reason']}")
            if t.get("pnl") is not None:
                total_pnl += t["pnl"]

        if day_trades:
            lines.append(f"Day P&L: ${total_pnl:+,.2f}")

        if day_notes:
            lines.append(f"\nNotes ({len(day_notes)}):")
            for n in day_notes:
                ts = datetime.fromtimestamp(n["timestamp"]).strftime("%H:%M")
                lines.append(f"  [{ts}] {n['text']}")

        if not day_trades and not day_notes:
            lines.append("No activity.")

        return "\n".join(lines)

    def export(self, format: str = "csv") -> str:
        """Export journal entries to CSV or JSON string."""
        if format == "json":
            return json.dumps(self._entries + self._notes, indent=2, default=str)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["timestamp", "type", "symbol", "side", "quantity", "price", "pnl", "reason/note"])
        for e in self._entries:
            writer.writerow([
                datetime.fromtimestamp(e["timestamp"]).isoformat(),
                "trade",
                e.get("symbol", ""),
                e.get("side", ""),
                e.get("quantity", ""),
                e.get("price", ""),
                e.get("pnl", ""),
                e.get("reason", ""),
            ])
        for n in self._notes:
            writer.writerow([
                datetime.fromtimestamp(n["timestamp"]).isoformat(),
                "note", "", "", "", "", "",
                n.get("text", ""),
            ])
        return output.getvalue()

    def performance_review(self, period: str = "1w") -> dict:
        """Review performance over a period (1d, 1w, 1m, 3m)."""
        days_map = {"1d": 1, "1w": 7, "1m": 30, "3m": 90}
        days = days_map.get(period, 7)
        cutoff = (datetime.now() - timedelta(days=days)).timestamp()

        trades = [
            e for e in self._entries
            if e["type"] == "trade" and e["timestamp"] >= cutoff
        ]

        sells = [t for t in trades if t["side"] == "SELL" and t.get("pnl") is not None]
        buys = [t for t in trades if t["side"] == "BUY"]

        total_pnl = sum(t["pnl"] for t in sells)
        wins = [t for t in sells if t["pnl"] > 0]
        losses = [t for t in sells if t["pnl"] < 0]

        symbols_traded = list(set(t["symbol"] for t in trades))

        return {
            "period": period,
            "total_trades": len(trades),
            "buys": len(buys),
            "sells": len(sells),
            "total_pnl": total_pnl,
            "win_count": len(wins),
            "loss_count": len(losses),
            "win_rate": (len(wins) / len(sells) * 100) if sells else 0.0,
            "avg_win": (sum(t["pnl"] for t in wins) / len(wins)) if wins else 0.0,
            "avg_loss": (sum(t["pnl"] for t in losses) / len(losses)) if losses else 0.0,
            "symbols_traded": symbols_traded,
            "notes_count": len([n for n in self._notes if n["timestamp"] >= cutoff]),
        }

    def get_entries(self) -> list[dict]:
        """Return all journal entries."""
        return list(self._entries)

    def get_notes(self) -> list[dict]:
        """Return all notes."""
        return list(self._notes)

    def _save(self) -> None:
        if not self.journal_path:
            return
        data = {"entries": self._entries, "notes": self._notes}
        os.makedirs(os.path.dirname(self.journal_path) or ".", exist_ok=True)
        with open(self.journal_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _load(self) -> None:
        if not self.journal_path or not os.path.exists(self.journal_path):
            return
        try:
            with open(self.journal_path) as f:
                data = json.load(f)
            self._entries = data.get("entries", [])
            self._notes = data.get("notes", [])
        except (json.JSONDecodeError, KeyError):
            pass
