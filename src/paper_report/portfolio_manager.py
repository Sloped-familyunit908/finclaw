"""
Paper Trading Portfolio Manager

Manages US and CN paper trading portfolios with JSON state persistence.
Generates daily reports and performance summaries.
"""

import json
import os
from datetime import datetime, date
from typing import Optional


# Default paths (relative to project root)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DEFAULT_DATA_DIR = os.path.join(_PROJECT_ROOT, "docs", "paper-trading")


class PortfolioManager:
    """Manages paper trading portfolios for US and CN markets."""

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or _DEFAULT_DATA_DIR
        self.reports_dir = os.path.join(self.data_dir, "reports")

    def _us_portfolio_path(self) -> str:
        return os.path.join(self.data_dir, "us-portfolio.json")

    def _cn_portfolio_path(self) -> str:
        return os.path.join(self.data_dir, "cn-portfolio.json")

    def _summary_path(self) -> str:
        return os.path.join(self.data_dir, "summary.md")

    def _report_path(self, report_date: str) -> str:
        return os.path.join(self.reports_dir, f"{report_date}.md")

    def init_portfolios(
        self,
        us_capital: float = 100_000.0,
        cn_capital: float = 1_000_000.0,
        start_date: Optional[str] = None,
    ) -> dict:
        """Initialize both US and CN portfolios with starting capital.

        Returns dict with both portfolio states.
        """
        if start_date is None:
            start_date = date.today().isoformat()

        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.reports_dir, exist_ok=True)

        us_portfolio = {
            "market": "US",
            "currency": "USD",
            "currency_symbol": "$",
            "start_date": start_date,
            "initial_capital": us_capital,
            "cash": us_capital,
            "positions": [],
            "trade_history": [],
            "daily_snapshots": [
                {
                    "date": start_date,
                    "total_value": us_capital,
                    "cash": us_capital,
                    "positions_value": 0.0,
                }
            ],
        }

        cn_portfolio = {
            "market": "CN",
            "currency": "CNY",
            "currency_symbol": "¥",
            "start_date": start_date,
            "initial_capital": cn_capital,
            "cash": cn_capital,
            "positions": [],
            "trade_history": [],
            "daily_snapshots": [
                {
                    "date": start_date,
                    "total_value": cn_capital,
                    "cash": cn_capital,
                    "positions_value": 0.0,
                }
            ],
        }

        self._save_json(self._us_portfolio_path(), us_portfolio)
        self._save_json(self._cn_portfolio_path(), cn_portfolio)

        # Generate initial summary
        self.generate_summary()

        return {"us": us_portfolio, "cn": cn_portfolio}

    def load_portfolio(self, market: str) -> Optional[dict]:
        """Load a portfolio by market ('US' or 'CN')."""
        path = self._us_portfolio_path() if market.upper() == "US" else self._cn_portfolio_path()
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_portfolio(self, market: str, portfolio: dict) -> None:
        """Save a portfolio back to disk."""
        path = self._us_portfolio_path() if market.upper() == "US" else self._cn_portfolio_path()
        self._save_json(path, portfolio)

    def get_portfolio_value(self, portfolio: dict) -> float:
        """Calculate total portfolio value (cash + positions)."""
        positions_value = sum(
            p.get("current_price", p.get("avg_cost", 0)) * p.get("shares", 0)
            for p in portfolio.get("positions", [])
        )
        return portfolio.get("cash", 0) + positions_value

    def get_portfolio_return(self, portfolio: dict) -> float:
        """Calculate portfolio return percentage."""
        initial = portfolio.get("initial_capital", 1)
        current = self.get_portfolio_value(portfolio)
        if initial == 0:
            return 0.0
        return (current / initial - 1) * 100

    def add_daily_snapshot(self, portfolio: dict, snapshot_date: Optional[str] = None) -> dict:
        """Add a daily snapshot to portfolio history."""
        if snapshot_date is None:
            snapshot_date = date.today().isoformat()

        total_value = self.get_portfolio_value(portfolio)
        positions_value = total_value - portfolio.get("cash", 0)

        snapshot = {
            "date": snapshot_date,
            "total_value": total_value,
            "cash": portfolio.get("cash", 0),
            "positions_value": positions_value,
        }

        portfolio.setdefault("daily_snapshots", []).append(snapshot)
        return snapshot

    def generate_daily_report(self, report_date: Optional[str] = None) -> str:
        """Generate a daily markdown report.

        Returns the report content as a string.
        """
        if report_date is None:
            report_date = date.today().isoformat()

        us = self.load_portfolio("US")
        cn = self.load_portfolio("CN")

        if us is None and cn is None:
            return "# Error\n\nNo portfolios found. Run `finclaw paper-report --init` first.\n"

        lines = [
            f"# 📊 Paper Trading Daily Report - {report_date}",
            "",
            "## Portfolio Summary",
            "",
            "| Portfolio | Cash | Positions Value | Total Value | Return |",
            "|-----------|------|-----------------|-------------|--------|",
        ]

        if us:
            us_value = self.get_portfolio_value(us)
            us_ret = self.get_portfolio_return(us)
            us_pos_val = us_value - us.get("cash", 0)
            lines.append(
                f"| US Stocks | ${us.get('cash', 0):,.2f} | ${us_pos_val:,.2f} | ${us_value:,.2f} | {us_ret:+.2f}% |"
            )

        if cn:
            cn_value = self.get_portfolio_value(cn)
            cn_ret = self.get_portfolio_return(cn)
            cn_pos_val = cn_value - cn.get("cash", 0)
            lines.append(
                f"| A-Shares | ¥{cn.get('cash', 0):,.2f} | ¥{cn_pos_val:,.2f} | ¥{cn_value:,.2f} | {cn_ret:+.2f}% |"
            )

        lines.extend([
            "",
            "## Signals & Actions",
            "",
            "*(No trades executed today — framework initialization)*",
            "",
            "## Notes",
            "",
            f"- Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "- Strategy: US=Multi-factor momentum + RSI mean-reversion, CN=FinClaw AI Scanner",
            "",
            "---",
            "*Individual positions are not disclosed. Only aggregate performance is shown.*",
            "",
        ])

        report = "\n".join(lines)

        # Save to file
        os.makedirs(self.reports_dir, exist_ok=True)
        report_path = self._report_path(report_date)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        return report

    def generate_summary(self) -> str:
        """Generate the summary.md performance overview.

        Returns the summary content as a string.
        """
        us = self.load_portfolio("US")
        cn = self.load_portfolio("CN")

        lines = [
            "# 📊 FinClaw Paper Trading Performance",
            "",
            "## Current Performance",
            "| Portfolio | Start Date | Starting Capital | Current Value | Return |",
            "|-----------|------------|------------------|---------------|--------|",
        ]

        if us:
            us_value = self.get_portfolio_value(us)
            us_ret = self.get_portfolio_return(us)
            lines.append(
                f"| US Stocks | {us['start_date']} | $"
                f"{us['initial_capital']:,.0f} | ${us_value:,.0f} | {us_ret:+.1f}% |"
            )

        if cn:
            cn_value = self.get_portfolio_value(cn)
            cn_ret = self.get_portfolio_return(cn)
            lines.append(
                f"| A-Shares | {cn['start_date']} | ¥"
                f"{cn['initial_capital']:,.0f} | ¥{cn_value:,.0f} | {cn_ret:+.1f}% |"
            )

        lines.extend([
            "",
            "## Strategy",
            "- US: Multi-factor momentum + RSI mean-reversion",
            "- CN: FinClaw AI Scanner (batch mode, 3-day hold)",
            "",
            "## Weekly Returns",
            "| Week | US | CN | Combined |",
            "|------|----|----|----------|",
        ])

        # Calculate weekly returns from snapshots
        weekly_data = self._calculate_weekly_returns(us, cn)
        if weekly_data:
            for week in weekly_data:
                lines.append(
                    f"| {week['label']} | {week['us']} | {week['cn']} | {week['combined']} |"
                )
        else:
            lines.append("| (starting...) | - | - | - |")

        lines.extend([
            "",
            "*Updated daily by automated pipeline. Past performance does not guarantee future results.*",
            "*Individual positions are not disclosed. Only aggregate performance is shown.*",
            "",
        ])

        summary = "\n".join(lines)

        os.makedirs(self.data_dir, exist_ok=True)
        with open(self._summary_path(), "w", encoding="utf-8") as f:
            f.write(summary)

        return summary

    def _calculate_weekly_returns(
        self,
        us: Optional[dict],
        cn: Optional[dict],
    ) -> list:
        """Calculate weekly returns from daily snapshots."""
        # Need at least 2 snapshots spanning 7+ days to show a week
        us_snaps = (us or {}).get("daily_snapshots", [])
        cn_snaps = (cn or {}).get("daily_snapshots", [])

        if len(us_snaps) < 6 and len(cn_snaps) < 6:
            return []

        weeks = []
        # Group by ISO week
        us_by_week = self._group_snapshots_by_week(us_snaps, us.get("initial_capital", 1) if us else 1)
        cn_by_week = self._group_snapshots_by_week(cn_snaps, cn.get("initial_capital", 1) if cn else 1)

        all_weeks = sorted(set(list(us_by_week.keys()) + list(cn_by_week.keys())))
        for week_label in all_weeks:
            us_ret = us_by_week.get(week_label)
            cn_ret = cn_by_week.get(week_label)
            us_str = f"{us_ret:+.1f}%" if us_ret is not None else "-"
            cn_str = f"{cn_ret:+.1f}%" if cn_ret is not None else "-"
            if us_ret is not None and cn_ret is not None:
                combined = (us_ret + cn_ret) / 2
                combined_str = f"{combined:+.1f}%"
            elif us_ret is not None:
                combined_str = us_str
            elif cn_ret is not None:
                combined_str = cn_str
            else:
                combined_str = "-"
            weeks.append({"label": week_label, "us": us_str, "cn": cn_str, "combined": combined_str})

        return weeks

    def _group_snapshots_by_week(self, snapshots: list, initial_capital: float) -> dict:
        """Group snapshots by ISO week and compute weekly return vs initial capital."""
        if not snapshots:
            return {}
        by_week = {}
        for snap in snapshots:
            d = date.fromisoformat(snap["date"])
            iso = d.isocalendar()
            week_label = f"W{iso[1]:02d}"
            by_week[week_label] = snap["total_value"]

        result = {}
        for week_label, value in by_week.items():
            ret = (value / initial_capital - 1) * 100
            result[week_label] = ret
        return result

    def _save_json(self, path: str, data: dict) -> None:
        """Save data as JSON."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
