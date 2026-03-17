"""Paper Trading Simulator - virtual portfolio management and strategy testing."""

from src.paper.engine import PaperTradingEngine, Order, Portfolio, PnL
from src.paper.dashboard import PaperDashboard
from src.paper.runner import StrategyRunner
from src.paper.journal import TradeJournal
from src.paper.realtime_dashboard import RealtimeDashboard, DashboardConfig, DashboardEvent, DashboardEventType

__all__ = [
    "PaperTradingEngine",
    "Order",
    "Portfolio",
    "PnL",
    "PaperDashboard",
    "StrategyRunner",
    "TradeJournal",
    "RealtimeDashboard",
    "DashboardConfig",
    "DashboardEvent",
    "DashboardEventType",
]
