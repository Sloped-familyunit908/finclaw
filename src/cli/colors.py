"""
Terminal color utilities for FinClaw CLI.
Uses ANSI escape codes — works on modern terminals (Windows 10+, macOS, Linux).
"""

import os
import sys

# Disable colors if NO_COLOR env var is set or not a TTY
_NO_COLOR = os.environ.get("NO_COLOR") or os.environ.get("FINCLAW_NO_COLOR")
_IS_TTY = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
COLORS_ENABLED = _IS_TTY and not _NO_COLOR


def _c(code: str, text: str) -> str:
    if not COLORS_ENABLED:
        return text
    return f"\033[{code}m{text}\033[0m"


# Basic colors
def red(t: str) -> str: return _c("31", t)
def green(t: str) -> str: return _c("32", t)
def yellow(t: str) -> str: return _c("33", t)
def blue(t: str) -> str: return _c("34", t)
def magenta(t: str) -> str: return _c("35", t)
def cyan(t: str) -> str: return _c("36", t)
def white(t: str) -> str: return _c("37", t)
def gray(t: str) -> str: return _c("90", t)
def bold(t: str) -> str: return _c("1", t)
def dim(t: str) -> str: return _c("2", t)

# Bright variants
def bright_red(t: str) -> str: return _c("91", t)
def bright_green(t: str) -> str: return _c("92", t)
def bright_yellow(t: str) -> str: return _c("93", t)
def bright_cyan(t: str) -> str: return _c("96", t)


def price_color(value: float, text: str = None) -> str:
    """Color a value: green if positive, red if negative, gray if zero."""
    if text is None:
        text = f"{value:+.2f}"
    if value > 0:
        return bright_green(text)
    elif value < 0:
        return bright_red(text)
    return gray(text)


def pct_color(value: float, text: str = None) -> str:
    """Color a percentage: green if positive, red if negative."""
    if text is None:
        text = f"{value:+.2%}"
    return price_color(value, text)


def signal_color(signal: str) -> str:
    """Color a signal word (BULLISH/BEARISH/NEUTRAL/OVERSOLD/OVERBOUGHT)."""
    s = signal.upper()
    if s in ("BULLISH", "OVERSOLD", "BUY", "ABOVE"):
        return bright_green(signal)
    elif s in ("BEARISH", "OVERBOUGHT", "SELL", "BELOW"):
        return bright_red(signal)
    return yellow(signal)


def header(text: str) -> str:
    """Format a section header."""
    return bold(cyan(text))


def success(text: str) -> str:
    return bright_green(f"✓ {text}")


def error(text: str) -> str:
    return bright_red(f"✗ {text}")


def banner() -> str:
    """FinClaw ASCII banner."""
    art = r"""
  ███████╗██╗███╗   ██╗ ██████╗██╗      █████╗ ██╗    ██╗
  ██╔════╝██║████╗  ██║██╔════╝██║     ██╔══██╗██║    ██║
  █████╗  ██║██╔██╗ ██║██║     ██║     ███████║██║ █╗ ██║
  ██╔══╝  ██║██║╚██╗██║██║     ██║     ██╔══██║██║███╗██║
  ██║     ██║██║ ╚████║╚██████╗███████╗██║  ██║╚███╔███╔╝
  ╚═╝     ╚═╝╚═╝  ╚═══╝ ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝
"""
    return cyan(art) + dim("  AI-Powered Financial Intelligence Engine\n")
