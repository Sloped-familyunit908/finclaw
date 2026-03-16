"""
FinClaw Setup Wizard v5.7.0
Interactive first-run setup: finclaw init
"""

import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from src.cli.config import ConfigManager, DEFAULT_CONFIG
from src.cli.formatter import OutputFormatter


EXCHANGES = [
    ("binance", "Binance (crypto)"),
    ("coinbase", "Coinbase (crypto)"),
    ("kraken", "Kraken (crypto)"),
    ("okx", "OKX (crypto)"),
    ("bybit", "Bybit (crypto)"),
    ("yfinance", "Yahoo Finance (stocks, free)"),
    ("alpaca", "Alpaca (stocks, US)"),
    ("interactive_brokers", "Interactive Brokers (multi-asset)"),
]

STRATEGIES = [
    ("momentum", "Momentum — follow the trend"),
    ("mean_reversion", "Mean Reversion — buy dips, sell peaks"),
    ("grid_trading", "Grid Trading — range-bound profits"),
    ("trend_following", "Trend Following — ride the wave"),
    ("buy_and_hold", "Buy & Hold — simple and steady"),
]


class SetupWizard:
    """Interactive setup wizard for first-time configuration."""

    def __init__(self, config_path: Optional[str] = None):
        self._config_path = config_path
        self._formatter = OutputFormatter()

    def run(self) -> bool:
        """Run the wizard. Returns True if config was saved."""
        self._print_welcome()

        try:
            # Step 1: Exchanges
            exchanges = self._step_exchanges()

            # Step 2: API keys
            api_keys = self._step_api_keys(exchanges)

            # Step 3: Default strategy
            strategy = self._step_strategy()

            # Step 4: Trading mode
            mode = self._step_mode()

            # Save
            return self._save_config(exchanges, api_keys, strategy, mode)

        except (KeyboardInterrupt, EOFError):
            print("\n\n  Setup cancelled. You can run 'finclaw init' anytime.\n")
            return False

    def _print_welcome(self) -> None:
        print()
        print(OutputFormatter.banner("Welcome to FinClaw!"))
        print()
        print("  Let's set up your environment. This takes about 30 seconds.")
        print("  You can change these settings later in ~/.finclaw/config.yaml")
        print()

    def _step_exchanges(self) -> List[str]:
        print("  [1/4] Which exchanges do you want to use?")
        print()
        for i, (key, desc) in enumerate(EXCHANGES, 1):
            print(f"    {i}. {desc}")
        print()
        print("  Enter numbers separated by commas (e.g., 1,6), or 'all':")
        raw = input("  > ").strip()

        if raw.lower() == "all":
            return [k for k, _ in EXCHANGES]

        selected = []
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(EXCHANGES):
                    selected.append(EXCHANGES[idx][0])

        if not selected:
            print("  No valid selection. Using yfinance as default.")
            selected = ["yfinance"]

        names = ", ".join(selected)
        print(f"  ✓ Selected: {names}\n")
        return selected

    def _step_api_keys(self, exchanges: List[str]) -> dict:
        print("  [2/4] Enter API keys (optional — press Enter to skip)")
        print()

        api_keys = {}
        skip_list = ["yfinance"]  # Free, no key needed

        for ex in exchanges:
            if ex in skip_list:
                print(f"    {ex}: free data, no key needed ✓")
                continue
            key = input(f"    {ex} API key (Enter to skip): ").strip()
            if key:
                secret = input(f"    {ex} API secret: ").strip()
                api_keys[ex] = {"api_key": key, "secret": secret}
                print(f"    ✓ {ex} key saved")
            else:
                print(f"    ⏭ Skipped {ex}")

        print()
        return api_keys

    def _step_strategy(self) -> str:
        print("  [3/4] Choose your default strategy:")
        print()
        for i, (key, desc) in enumerate(STRATEGIES, 1):
            print(f"    {i}. {desc}")
        print()
        raw = input("  > ").strip()

        if raw.isdigit() and 1 <= int(raw) <= len(STRATEGIES):
            choice = STRATEGIES[int(raw) - 1][0]
        else:
            choice = "momentum"

        print(f"  ✓ Default strategy: {choice}\n")
        return choice

    def _step_mode(self) -> str:
        print("  [4/4] Trading mode:")
        print()
        print("    1. Paper trading (simulated, safe)")
        print("    2. Live trading (real money — careful!)")
        print()
        raw = input("  > ").strip()

        mode = "live" if raw == "2" else "paper"
        emoji = "🔴" if mode == "live" else "📝"
        print(f"  ✓ Mode: {mode} {emoji}\n")
        return mode

    def _save_config(self, exchanges: List[str], api_keys: dict,
                     strategy: str, mode: str) -> bool:
        config = ConfigManager(self._config_path)
        config.set("exchanges", exchanges)
        config.set("default_exchange", exchanges[0] if exchanges else "yfinance")
        config.set("api_keys", api_keys)
        config.set("default_strategy", strategy)
        config.set("mode", mode)
        config.save()

        print(f"  ✅ Config saved to {config.path}")
        print()
        print("  Quick start:")
        print("    finclaw quote BTCUSDT        # Get a quote")
        print("    finclaw shell                 # Interactive mode")
        print("    finclaw backtest momentum     # Run a backtest")
        print()
        return True
