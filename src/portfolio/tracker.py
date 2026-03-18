"""
FinClaw Portfolio Tracker
=========================
Local portfolio tracker with JSON persistence, P&L tracking,
allocation analysis, history snapshots, price alerts, and CSV export.

Storage: ~/.finclaw/portfolio.json (default)
Supports multiple named portfolios via --portfolio flag.
"""

import csv
import io
import json
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from pathlib import Path
from typing import Optional


@dataclass
class Holding:
    symbol: str
    quantity: float
    avg_cost: float  # weighted average buy price
    added_at: str = ""  # ISO timestamp

    def __post_init__(self):
        if not self.added_at:
            self.added_at = datetime.now().isoformat()


@dataclass
class Alert:
    symbol: str
    condition: str  # "above" or "below"
    threshold: float
    created_at: str = ""
    triggered: bool = False

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class HistorySnapshot:
    date: str  # YYYY-MM-DD
    total_value: float
    total_cost: float
    holdings_count: int


@dataclass
class PortfolioData:
    name: str = "main"
    holdings: list = field(default_factory=list)
    alerts: list = field(default_factory=list)
    history: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "holdings": [asdict(h) if isinstance(h, Holding) else h for h in self.holdings],
            "alerts": [asdict(a) if isinstance(a, Alert) else a for a in self.alerts],
            "history": [asdict(s) if isinstance(s, HistorySnapshot) else s for s in self.history],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PortfolioData":
        pf = cls(name=data.get("name", "main"))
        pf.holdings = [Holding(**h) if isinstance(h, dict) else h for h in data.get("holdings", [])]
        pf.alerts = [Alert(**a) if isinstance(a, dict) else a for a in data.get("alerts", [])]
        pf.history = [HistorySnapshot(**s) if isinstance(s, dict) else s for s in data.get("history", [])]
        return pf


class PortfolioTracker:
    """Manage a local portfolio stored as JSON."""

    def __init__(self, storage_path: Optional[str] = None, portfolio_name: str = "main",
                 price_fetcher=None):
        """
        Args:
            storage_path: Path to the portfolio JSON file. Default: ~/.finclaw/portfolio.json
            portfolio_name: Name of the portfolio within the file.
            price_fetcher: Callable(symbol) -> float. Injected for testing.
        """
        if storage_path is None:
            storage_path = os.path.join(Path.home(), ".finclaw", "portfolio.json")
        self.storage_path = storage_path
        self.portfolio_name = portfolio_name
        self._price_fetcher = price_fetcher or self._default_price_fetcher
        self._data: Optional[PortfolioData] = None

    # ── persistence ─────────────────────────────────────────────
    def _ensure_dir(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

    def _load_all(self) -> dict:
        """Load the entire JSON file (may contain multiple portfolios)."""
        if not os.path.exists(self.storage_path):
            return {}
        with open(self.storage_path, "r") as f:
            return json.load(f)

    def _save_all(self, all_data: dict):
        self._ensure_dir()
        with open(self.storage_path, "w") as f:
            json.dump(all_data, f, indent=2, default=str)

    def load(self) -> PortfolioData:
        all_data = self._load_all()
        raw = all_data.get(self.portfolio_name, {"name": self.portfolio_name})
        self._data = PortfolioData.from_dict(raw)
        return self._data

    def save(self) -> None:
        if self._data is None:
            return
        all_data = self._load_all()
        all_data[self.portfolio_name] = self._data.to_dict()
        self._save_all(all_data)

    @property
    def data(self) -> PortfolioData:
        if self._data is None:
            self.load()
        return self._data

    # ── price fetching ──────────────────────────────────────────
    @staticmethod
    def _default_price_fetcher(symbol: str) -> Optional[float]:
        """Fetch latest price via yfinance (best-effort)."""
        try:
            import yfinance as yf
            import logging
            import warnings
            logging.getLogger("yfinance").setLevel(logging.CRITICAL)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                t = yf.Ticker(symbol)
                hist = t.history(period="5d")
            if hist is not None and not hist.empty:
                return float(hist["Close"].iloc[-1])
        except Exception:
            pass  # Optional: price fetch is best-effort; returns None on failure
        return None

    def get_price(self, symbol: str) -> Optional[float]:
        return self._price_fetcher(symbol)

    # ── add / remove ────────────────────────────────────────────
    def add(self, symbol: str, quantity: float, buy_price: float = 0.0) -> Holding:
        """Add a holding. If symbol exists, update weighted avg cost."""
        symbol = symbol.upper()
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if buy_price < 0:
            raise ValueError("Buy price cannot be negative")

        existing = self._find_holding(symbol)
        if existing:
            total_cost = existing.avg_cost * existing.quantity + buy_price * quantity
            existing.quantity += quantity
            existing.avg_cost = total_cost / existing.quantity if existing.quantity > 0 else 0
        else:
            h = Holding(symbol=symbol, quantity=quantity, avg_cost=buy_price)
            self.data.holdings.append(h)
            existing = h

        self.save()
        return existing

    def remove(self, symbol: str, quantity: float) -> Optional[Holding]:
        """Remove quantity from a holding. Removes entirely if quantity >= held."""
        symbol = symbol.upper()
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        existing = self._find_holding(symbol)
        if existing is None:
            raise ValueError(f"No holding found for {symbol}")

        existing.quantity -= quantity
        if existing.quantity <= 1e-12:
            self.data.holdings = [h for h in self.data.holdings if h.symbol != symbol]
            existing = None

        self.save()
        return existing

    def _find_holding(self, symbol: str) -> Optional[Holding]:
        for h in self.data.holdings:
            if h.symbol == symbol:
                return h
        return None

    # ── show / P&L ──────────────────────────────────────────────
    def show(self) -> dict:
        """Return current portfolio status with P&L per holding and total."""
        rows = []
        total_value = 0.0
        total_cost = 0.0

        for h in self.data.holdings:
            price = self.get_price(h.symbol)
            if price is None:
                price = h.avg_cost  # fallback

            value = h.quantity * price
            cost = h.quantity * h.avg_cost
            pnl = value - cost
            pnl_pct = (pnl / cost) if cost > 0 else 0.0

            rows.append({
                "symbol": h.symbol,
                "quantity": h.quantity,
                "avg_cost": h.avg_cost,
                "price": price,
                "value": value,
                "cost": cost,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
            })
            total_value += value
            total_cost += cost

        total_pnl = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost) if total_cost > 0 else 0.0

        return {
            "portfolio": self.portfolio_name,
            "holdings": rows,
            "total_value": total_value,
            "total_cost": total_cost,
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
        }

    # ── allocation ──────────────────────────────────────────────
    def allocation(self) -> list[dict]:
        """Return % allocation by asset."""
        status = self.show()
        total = status["total_value"]
        if total <= 0:
            return []
        return [
            {"symbol": r["symbol"], "value": r["value"],
             "pct": r["value"] / total * 100}
            for r in status["holdings"]
        ]

    # ── history snapshots ───────────────────────────────────────
    def snapshot(self) -> None:
        """Take a daily value snapshot and append to history."""
        status = self.show()
        today = date.today().isoformat()

        # Replace today's snapshot if exists
        self.data.history = [s for s in self.data.history if s.date != today]
        snap = HistorySnapshot(
            date=today,
            total_value=status["total_value"],
            total_cost=status["total_cost"],
            holdings_count=len(status["holdings"]),
        )
        self.data.history.append(snap)
        self.save()
        return snap

    def get_history(self) -> list[dict]:
        return [asdict(s) if isinstance(s, HistorySnapshot) else s for s in self.data.history]

    # ── alerts ──────────────────────────────────────────────────
    def add_alert(self, symbol: str, above: Optional[float] = None,
                  below: Optional[float] = None) -> Alert:
        symbol = symbol.upper()
        if above is not None:
            alert = Alert(symbol=symbol, condition="above", threshold=above)
        elif below is not None:
            alert = Alert(symbol=symbol, condition="below", threshold=below)
        else:
            raise ValueError("Specify --above or --below threshold")
        self.data.alerts.append(alert)
        self.save()
        return alert

    def check_alerts(self) -> list[dict]:
        """Check all alerts against current prices. Return triggered ones."""
        triggered = []
        for alert in self.data.alerts:
            if alert.triggered:
                continue
            price = self.get_price(alert.symbol)
            if price is None:
                continue
            fire = False
            if alert.condition == "above" and price >= alert.threshold:
                fire = True
            elif alert.condition == "below" and price <= alert.threshold:
                fire = True
            if fire:
                alert.triggered = True
                triggered.append({
                    "symbol": alert.symbol,
                    "condition": alert.condition,
                    "threshold": alert.threshold,
                    "price": price,
                })
        if triggered:
            self.save()
        return triggered

    def list_alerts(self) -> list[dict]:
        return [asdict(a) if isinstance(a, Alert) else a for a in self.data.alerts]

    # ── export ──────────────────────────────────────────────────
    def export_csv(self, what: str = "holdings") -> str:
        """Export holdings or history as CSV string."""
        output = io.StringIO()
        if what == "holdings":
            status = self.show()
            writer = csv.DictWriter(output, fieldnames=[
                "symbol", "quantity", "avg_cost", "price", "value", "cost", "pnl", "pnl_pct",
            ])
            writer.writeheader()
            for row in status["holdings"]:
                writer.writerow({k: round(v, 4) if isinstance(v, float) else v for k, v in row.items()})
        elif what == "history":
            history = self.get_history()
            if history:
                writer = csv.DictWriter(output, fieldnames=list(history[0].keys()))
                writer.writeheader()
                for row in history:
                    writer.writerow(row)
        return output.getvalue()

    def export_to_file(self, filepath: str, what: str = "holdings") -> None:
        """Write CSV export to a file."""
        content = self.export_csv(what)
        with open(filepath, "w", newline="") as f:
            f.write(content)
