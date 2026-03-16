"""
FinClaw CLI Package v5.7.0
Interactive mode, rich formatting, setup wizard, and configuration.
"""

from src.cli.formatter import OutputFormatter
from src.cli.config import ConfigManager as CLIConfigManager

__all__ = ["OutputFormatter", "CLIConfigManager"]
