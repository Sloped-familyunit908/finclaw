"""
FinClaw Rich Output Formatter v5.7.0
Beautiful terminal output: tables, quote cards, sparklines, progress bars, colors.
"""

import math
import os
import shutil
from typing import Any, Dict, List, Optional, Tuple


# ANSI color codes
COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "bright_red": "\033[91m",
    "bright_green": "\033[92m",
    "bright_yellow": "\033[93m",
    "bright_blue": "\033[94m",
    "bright_magenta": "\033[95m",
    "bright_cyan": "\033[96m",
    "bg_red": "\033[41m",
    "bg_green": "\033[42m",
    "bg_blue": "\033[44m",
}

# Box drawing characters
BOX = {
    "tl": "┌", "tr": "┐", "bl": "└", "br": "┘",
    "h": "─", "v": "│", "lj": "├", "rj": "┤",
    "tj": "┬", "bj": "┴", "cross": "┼",
}

SPARKLINE_CHARS = "▁▂▃▄▅▆▇█"


def _no_color() -> bool:
    """Check if color output should be disabled."""
    return os.environ.get("NO_COLOR") is not None or os.environ.get("FINCLAW_NO_COLOR") is not None


def _terminal_width() -> int:
    """Get terminal width, default 80."""
    try:
        return shutil.get_terminal_size((80, 24)).columns
    except Exception:
        return 80


class OutputFormatter:
    """Rich terminal output for FinClaw."""

    @staticmethod
    def color(text: str, color_name: str) -> str:
        """Wrap text in ANSI color codes."""
        if _no_color():
            return text
        code = COLORS.get(color_name, "")
        if not code:
            return text
        return f"{code}{text}{COLORS['reset']}"

    @staticmethod
    def bold(text: str) -> str:
        """Bold text."""
        if _no_color():
            return text
        return f"{COLORS['bold']}{text}{COLORS['reset']}"

    @staticmethod
    def price_color(value: float, text: str = None) -> str:
        """Color text green for positive, red for negative."""
        display = text if text is not None else f"{value:+.2%}"
        if value > 0:
            return OutputFormatter.color(display, "bright_green")
        elif value < 0:
            return OutputFormatter.color(display, "bright_red")
        return display

    @staticmethod
    def table(headers: List[str], rows: List[List[Any]], style: str = "default") -> str:
        """Render a formatted table.

        Args:
            headers: Column header names.
            rows: List of row data (each row is a list of values).
            style: 'default' (box-drawn), 'compact', or 'simple'.

        Returns:
            Formatted table string.
        """
        if not headers:
            return ""

        # Calculate column widths
        str_rows = [[str(c) for c in row] for row in rows]
        widths = [len(h) for h in headers]
        for row in str_rows:
            for i, cell in enumerate(row):
                if i < len(widths):
                    widths[i] = max(widths[i], len(cell))

        if style == "simple":
            lines = []
            header_line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
            lines.append(header_line)
            lines.append("  ".join("-" * w for w in widths))
            for row in str_rows:
                lines.append("  ".join(
                    (row[i] if i < len(row) else "").ljust(widths[i])
                    for i in range(len(headers))
                ))
            return "\n".join(lines)

        if style == "compact":
            lines = []
            header_line = " │ ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
            lines.append(header_line)
            lines.append("─┼─".join("─" * w for w in widths))
            for row in str_rows:
                lines.append(" │ ".join(
                    (row[i] if i < len(row) else "").ljust(widths[i])
                    for i in range(len(headers))
                ))
            return "\n".join(lines)

        # Default: box-drawn table
        h_line = BOX["h"]
        sep = f"{h_line}{BOX['tj']}{h_line}".join(h_line * (w + 2) for w in widths)
        top = f"{BOX['tl']}{h_line}{sep[1:-1]}{h_line}{BOX['tr']}"  # simplified
        # Build properly
        inner_top = BOX["tj"].join(BOX["h"] * (w + 2) for w in widths)
        inner_mid = BOX["cross"].join(BOX["h"] * (w + 2) for w in widths)
        inner_bot = BOX["bj"].join(BOX["h"] * (w + 2) for w in widths)

        top = f"{BOX['tl']}{inner_top}{BOX['tr']}"
        mid = f"{BOX['lj']}{inner_mid}{BOX['rj']}"
        bot = f"{BOX['bl']}{inner_bot}{BOX['br']}"

        def fmt_row(cells):
            parts = []
            for i, w in enumerate(widths):
                c = cells[i] if i < len(cells) else ""
                parts.append(f" {c.ljust(w)} ")
            return BOX["v"] + BOX["v"].join(parts) + BOX["v"]

        lines = [top, fmt_row(headers), mid]
        for row in str_rows:
            lines.append(fmt_row(row))
        lines.append(bot)
        return "\n".join(lines)

    @staticmethod
    def quote_card(quote: Dict[str, Any]) -> str:
        """Render a beautiful quote card.

        Expected keys: symbol, price, change_pct, volume (optional),
                       high (optional), low (optional).
        """
        symbol = quote.get("symbol", "???")
        price = quote.get("price", 0.0)
        change = quote.get("change_pct", 0.0)
        volume = quote.get("volume")
        high = quote.get("high")
        low = quote.get("low")

        # Format price
        if price >= 1000:
            price_str = f"${price:,.2f}"
        elif price >= 1:
            price_str = f"${price:.2f}"
        else:
            price_str = f"${price:.6f}"

        # Format change
        arrow = "▲" if change >= 0 else "▼"
        change_str = f"{arrow} {change:+.2f}%"

        # Format volume
        vol_str = ""
        if volume is not None:
            if volume >= 1e9:
                vol_str = f"Vol: {volume/1e9:.1f}B"
            elif volume >= 1e6:
                vol_str = f"Vol: {volume/1e6:.1f}M"
            elif volume >= 1e3:
                vol_str = f"Vol: {volume/1e3:.0f}K"
            else:
                vol_str = f"Vol: {volume:.0f}"

        # Build card content
        line1_left = symbol
        line1_right = price_str
        line2_left = change_str
        line2_right = vol_str

        # Calculate card width
        inner_w = max(
            len(line1_left) + len(line1_right) + 4,
            len(line2_left) + len(line2_right) + 4,
            25,
        )

        def pad_line(left, right, width):
            gap = width - len(left) - len(right)
            return f"{left}{' ' * max(gap, 1)}{right}"

        top = f"┌{'─' * (inner_w + 2)}┐"
        bot = f"└{'─' * (inner_w + 2)}┘"
        l1 = f"│ {pad_line(line1_left, line1_right, inner_w)} │"
        l2 = f"│ {pad_line(line2_left, line2_right, inner_w)} │"

        card = f"{top}\n{l1}\n{l2}"

        # Optional high/low line
        if high is not None and low is not None:
            hl_str = pad_line(f"H: {high:.2f}", f"L: {low:.2f}", inner_w)
            card += f"\n│ {hl_str} │"

        card += f"\n{bot}"

        # Apply colors
        if not _no_color():
            if change >= 0:
                card_color = COLORS["bright_green"]
            else:
                card_color = COLORS["bright_red"]
            # Color just the change line
            lines = card.split("\n")
            colored_lines = []
            for i, line in enumerate(lines):
                if i == 2:  # change line
                    colored_lines.append(f"{card_color}{line}{COLORS['reset']}")
                else:
                    colored_lines.append(line)
            card = "\n".join(colored_lines)

        return card

    @staticmethod
    def sparkline(values: List[float], width: Optional[int] = None) -> str:
        """Render a sparkline from a list of values.

        Args:
            values: Numeric values to plot.
            width: Max width (resamples if needed). None = use all values.

        Returns:
            Unicode sparkline string, e.g. '▁▂▃▅▇█▇▅▃'
        """
        if not values:
            return ""

        # Resample if needed
        if width and len(values) > width:
            step = len(values) / width
            resampled = []
            for i in range(width):
                idx = int(i * step)
                resampled.append(values[min(idx, len(values) - 1)])
            values = resampled

        mn, mx = min(values), max(values)
        rng = mx - mn if mx != mn else 1.0
        n = len(SPARKLINE_CHARS) - 1

        return "".join(
            SPARKLINE_CHARS[min(int((v - mn) / rng * n), n)]
            for v in values
        )

    @staticmethod
    def progress_bar(current: float, total: float, width: int = 30,
                     label: str = "", show_pct: bool = True) -> str:
        """Render a progress bar.

        Args:
            current: Current progress value.
            total: Total value.
            width: Bar width in characters.
            label: Optional label prefix.
            show_pct: Show percentage at end.

        Returns:
            Progress bar string, e.g. '███████░░░░░░░ 50%'
        """
        if total <= 0:
            pct = 0.0
        else:
            pct = min(current / total, 1.0)

        filled = int(pct * width)
        empty = width - filled
        bar = "█" * filled + "░" * empty

        result = f"{bar}"
        if show_pct:
            result += f" {pct:.0%}"
        if label:
            result = f"{label} {result}"

        return result

    @staticmethod
    def format_number(value: float, precision: int = 2) -> str:
        """Smart number formatting with suffixes."""
        if abs(value) >= 1e12:
            return f"{value/1e12:.{precision}f}T"
        elif abs(value) >= 1e9:
            return f"{value/1e9:.{precision}f}B"
        elif abs(value) >= 1e6:
            return f"{value/1e6:.{precision}f}M"
        elif abs(value) >= 1e3:
            return f"{value/1e3:.{precision}f}K"
        else:
            return f"{value:.{precision}f}"

    @staticmethod
    def banner(text: str, width: Optional[int] = None) -> str:
        """Render a centered banner."""
        w = width or min(_terminal_width(), 60)
        pad = max((w - len(text) - 2) // 2, 0)
        line = "═" * w
        return f"╔{line}╗\n║{' ' * pad} {text} {' ' * (w - pad - len(text) - 2)}║\n╚{line}╝"

    @staticmethod
    def divider(char: str = "─", width: Optional[int] = None) -> str:
        """Horizontal divider line."""
        w = width or min(_terminal_width(), 60)
        return char * w

    @staticmethod
    def key_value(data: Dict[str, Any], separator: str = ": ") -> str:
        """Format key-value pairs aligned."""
        if not data:
            return ""
        max_key = max(len(str(k)) for k in data.keys())
        lines = []
        for k, v in data.items():
            lines.append(f"  {str(k).rjust(max_key)}{separator}{v}")
        return "\n".join(lines)
