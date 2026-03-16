"""Smart Alert System v5.10."""
from .alert_engine import AlertEngine as LegacyAlertEngine, AlertCondition as LegacyAlertCondition, Alert as LegacyAlert
from .alert_manager import AlertManager, AlertSeverity as LegacyAlertSeverity, drawdown_alert, volatility_spike, correlation_break, volume_anomaly
from .alert_manager import Alert as ManagedAlert
from .engine import (
    AlertEngine, AlertCondition, AlertSeverity, AlertRule,
    PriceAlert, VolumeAlert, TechnicalAlert, SentimentAlert, PortfolioAlert,
    FiredAlert, AlertChannel,
)
from .channels import ConsoleChannel, WebhookChannel, FileChannel, EmailChannel
from .history import AlertHistory

__all__ = [
    # New smart alert system
    "AlertEngine", "AlertCondition", "AlertSeverity", "AlertRule",
    "PriceAlert", "VolumeAlert", "TechnicalAlert", "SentimentAlert", "PortfolioAlert",
    "FiredAlert", "AlertChannel",
    "ConsoleChannel", "WebhookChannel", "FileChannel", "EmailChannel",
    "AlertHistory",
    # Legacy
    "LegacyAlertEngine", "LegacyAlertCondition", "LegacyAlert",
    "AlertManager", "LegacyAlertSeverity", "ManagedAlert",
    "drawdown_alert", "volatility_spike", "correlation_break", "volume_anomaly",
]
