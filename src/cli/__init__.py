"""
FinClaw CLI Package v5.14.0
Interactive mode, rich formatting, setup wizard, and configuration.
"""

from src.cli.formatter import OutputFormatter
from src.cli.config import ConfigManager as CLIConfigManager
from src.cli.main import main, build_parser

__all__ = ["OutputFormatter", "CLIConfigManager", "main", "build_parser"]
