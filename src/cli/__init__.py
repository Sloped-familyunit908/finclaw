"""
FinClaw CLI Package v5.14.0
Interactive mode, rich formatting, setup wizard, and configuration.
"""

from src.cli.formatter import OutputFormatter
from src.cli.config import ConfigManager as CLIConfigManager

# We intentionally do NOT import from src.cli.main here.
#
# If we did ``from src.cli.main import main``, it would work fine for normal
# usage, BUT it causes a RuntimeWarning when someone runs:
#   python -m src.cli.main
# or
#   python -m src.cli
#
# The warning:
#   RuntimeWarning: 'src.cli.main' found in sys.modules after import of
#   package 'src.cli', but prior to execution of 'src.cli.main'
#
# Callers should import directly:
#   from src.cli.main import main

__all__ = ["OutputFormatter", "CLIConfigManager"]
