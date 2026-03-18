"""
FinClaw Doctor — diagnostic command to verify environment health.

Checks:
  - Python version compatibility
  - Required dependencies installed
  - Optional dependencies available
  - API key configuration
  - Network connectivity to exchanges
"""

from __future__ import annotations

import importlib
import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"


@dataclass
class DoctorResult:
    """Result of a single diagnostic check."""

    name: str
    passed: bool
    severity: Severity
    message: str
    fix_hint: str | None = None


class DoctorCheck:
    """Runs individual diagnostic checks."""

    # Python version bounds
    MIN_PYTHON = (3, 9)
    MAX_PYTHON = (3, 13)

    # Required dependencies (must be installed for core functionality)
    REQUIRED_DEPS: list[tuple[str, str]] = [
        ("numpy", "numpy"),
        ("pyyaml", "yaml"),
        ("scipy", "scipy"),
        ("aiohttp", "aiohttp"),
    ]

    # Optional dependencies (enhance functionality)
    OPTIONAL_DEPS: list[tuple[str, str, str]] = [
        ("yfinance", "yfinance", "Real-time market data from Yahoo Finance"),
        ("pandas", "pandas", "DataFrame support for data analysis"),
        ("backtrader", "backtrader", "Backtrader strategy adapter"),
        ("matplotlib", "matplotlib", "Chart generation"),
        ("plotly", "plotly", "Interactive charts"),
        ("redis", "redis", "Redis cache backend"),
        ("websockets", "websockets", "WebSocket connections"),
    ]

    # API keys to check (env var name → description)
    API_KEYS: list[tuple[str, str]] = [
        ("BINANCE_API_KEY", "Binance exchange"),
        ("BINANCE_API_SECRET", "Binance exchange secret"),
        ("ALPACA_API_KEY", "Alpaca trading"),
        ("ALPACA_API_SECRET", "Alpaca trading secret"),
        ("POLYGON_API_KEY", "Polygon.io market data"),
        ("ALPHA_VANTAGE_API_KEY", "Alpha Vantage market data"),
        ("OPENAI_API_KEY", "OpenAI (AI strategy generation)"),
        ("ANTHROPIC_API_KEY", "Anthropic (AI strategy generation)"),
        ("DEEPSEEK_API_KEY", "DeepSeek (AI strategy generation)"),
        ("TUSHARE_TOKEN", "TuShare (China A-share data)"),
    ]

    # Exchange endpoints to ping
    EXCHANGE_ENDPOINTS: list[tuple[str, str]] = [
        ("Yahoo Finance", "https://query1.finance.yahoo.com/v8/finance/chart/AAPL?range=1d"),
        ("Binance", "https://api.binance.com/api/v3/ping"),
        ("CoinGecko", "https://api.coingecko.com/api/v3/ping"),
        ("DeFi Llama", "https://api.llama.fi/protocols"),
    ]

    def check_python_version(self) -> DoctorResult:
        """Check Python version is within supported range."""
        version = sys.version_info[:2]
        version_str = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        if version < self.MIN_PYTHON:
            return DoctorResult(
                name="Python Version",
                passed=False,
                severity=Severity.REQUIRED,
                message=f"Python {version_str} is too old (need >= {self.MIN_PYTHON[0]}.{self.MIN_PYTHON[1]})",
                fix_hint=f"Install Python >= {self.MIN_PYTHON[0]}.{self.MIN_PYTHON[1]}",
            )

        if version >= self.MAX_PYTHON:
            return DoctorResult(
                name="Python Version",
                passed=True,
                severity=Severity.REQUIRED,
                message=f"Python {version_str} (untested, may have issues with >= {self.MAX_PYTHON[0]}.{self.MAX_PYTHON[1]})",
            )

        return DoctorResult(
            name="Python Version",
            passed=True,
            severity=Severity.REQUIRED,
            message=f"Python {version_str}",
        )

    def check_required_deps(self) -> list[DoctorResult]:
        """Check all required dependencies are installed."""
        results: list[DoctorResult] = []
        for pkg_name, import_name in self.REQUIRED_DEPS:
            try:
                mod = importlib.import_module(import_name)
                version = getattr(mod, "__version__", "unknown")
                results.append(DoctorResult(
                    name=f"Dep: {pkg_name}",
                    passed=True,
                    severity=Severity.REQUIRED,
                    message=f"{pkg_name} {version}",
                ))
            except ImportError:
                results.append(DoctorResult(
                    name=f"Dep: {pkg_name}",
                    passed=False,
                    severity=Severity.REQUIRED,
                    message=f"{pkg_name} not installed",
                    fix_hint=f"pip install {pkg_name}",
                ))
        return results

    def check_optional_deps(self) -> list[DoctorResult]:
        """Check optional dependencies."""
        results: list[DoctorResult] = []
        for pkg_name, import_name, desc in self.OPTIONAL_DEPS:
            try:
                mod = importlib.import_module(import_name)
                version = getattr(mod, "__version__", "unknown")
                results.append(DoctorResult(
                    name=f"Optional: {pkg_name}",
                    passed=True,
                    severity=Severity.OPTIONAL,
                    message=f"{pkg_name} {version} — {desc}",
                ))
            except ImportError:
                results.append(DoctorResult(
                    name=f"Optional: {pkg_name}",
                    passed=False,
                    severity=Severity.OPTIONAL,
                    message=f"{pkg_name} not installed — {desc}",
                    fix_hint=f"pip install {pkg_name}",
                ))
        return results

    def check_api_keys(self) -> list[DoctorResult]:
        """Check API key configuration."""
        results: list[DoctorResult] = []
        for env_var, desc in self.API_KEYS:
            value = os.environ.get(env_var)
            if value:
                # Mask the key for security
                masked = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
                results.append(DoctorResult(
                    name=f"API: {desc}",
                    passed=True,
                    severity=Severity.OPTIONAL,
                    message=f"{env_var} = {masked}",
                ))
            else:
                results.append(DoctorResult(
                    name=f"API: {desc}",
                    passed=False,
                    severity=Severity.OPTIONAL,
                    message=f"{env_var} not set",
                    fix_hint=f"export {env_var}=your_key_here",
                ))
        return results

    def check_exchange_connectivity(self) -> list[DoctorResult]:
        """Check network connectivity to exchange APIs."""
        import urllib.request
        import urllib.error

        results: list[DoctorResult] = []
        for name, url in self.EXCHANGE_ENDPOINTS:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "finclaw-doctor/1.0"})
                resp = urllib.request.urlopen(req, timeout=5)
                status = resp.getcode()
                results.append(DoctorResult(
                    name=f"Network: {name}",
                    passed=True,
                    severity=Severity.OPTIONAL,
                    message=f"{name} reachable (HTTP {status})",
                ))
            except urllib.error.URLError as e:
                results.append(DoctorResult(
                    name=f"Network: {name}",
                    passed=False,
                    severity=Severity.OPTIONAL,
                    message=f"{name} unreachable — {e.reason}",
                    fix_hint="Check your network connection or firewall settings",
                ))
            except Exception as e:
                results.append(DoctorResult(
                    name=f"Network: {name}",
                    passed=False,
                    severity=Severity.OPTIONAL,
                    message=f"{name} error — {e}",
                ))
        return results


def run_doctor(skip_network: bool = False) -> list[DoctorResult]:
    """Run all diagnostic checks and return results.

    Args:
        skip_network: If True, skip network connectivity checks.

    Returns:
        List of DoctorResult objects.
    """
    check = DoctorCheck()
    results: list[DoctorResult] = []

    # Python version
    results.append(check.check_python_version())

    # Required deps
    results.extend(check.check_required_deps())

    # Optional deps
    results.extend(check.check_optional_deps())

    # API keys
    results.extend(check.check_api_keys())

    # Exchange connectivity
    if not skip_network:
        results.extend(check.check_exchange_connectivity())

    return results


def format_doctor_output(results: list[DoctorResult], verbose: bool = False) -> str:
    """Format doctor results for terminal output.

    Args:
        results: List of DoctorResult from run_doctor().
        verbose: If True, show all checks; otherwise only failures and summary.

    Returns:
        Formatted string for printing.
    """
    lines: list[str] = []
    lines.append("")
    lines.append("  🩺 FinClaw Doctor")
    lines.append("  " + "─" * 60)

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    required_fails = [r for r in results if not r.passed and r.severity == Severity.REQUIRED]

    for r in results:
        if not verbose and r.passed:
            continue
        icon = "✅" if r.passed else ("❌" if r.severity == Severity.REQUIRED else "⚠️")
        lines.append(f"  {icon} {r.name}: {r.message}")
        if r.fix_hint and not r.passed:
            lines.append(f"     💡 {r.fix_hint}")

    if verbose:
        lines.append("")
        lines.append("  " + "─" * 60)

    lines.append(f"  Summary: {passed} passed, {failed} issues")

    if required_fails:
        lines.append(f"  ❌ {len(required_fails)} required check(s) failed!")
        lines.append("     Fix these before using FinClaw.")
    else:
        lines.append("  ✅ All required checks passed!")

    lines.append("")
    return "\n".join(lines)
