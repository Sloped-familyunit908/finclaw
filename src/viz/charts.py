"""Pure Python terminal charts — no external dependencies.

Unicode box-drawing, braille dots, ANSI colors for rich terminal output.
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple


# ANSI helpers
_GREEN = "\033[32m"
_RED = "\033[31m"
_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"

# Heatmap color ramp (blue → white → red)
_HEAT_COLORS = [
    "\033[34m",  # deep blue  (-1.0)
    "\033[36m",  # cyan       (-0.5)
    "\033[37m",  # white      ( 0.0)
    "\033[33m",  # yellow     (+0.5)
    "\033[31m",  # red        (+1.0)
]
_HEAT_BLOCKS = "░▒▓█"


class TerminalChart:
    """Collection of static terminal chart renderers."""

    # ------------------------------------------------------------------
    # Candlestick
    # ------------------------------------------------------------------
    @staticmethod
    def candlestick(
        data: list,
        width: int = 80,
        height: int = 20,
    ) -> str:
        """Render a Unicode candlestick chart.

        *data* is a list of dicts with keys: open, high, low, close.
        Uses ┃ for the candle body and │ for wicks, colored green/red.
        """
        if not data:
            return "(no data)"

        n = len(data)
        # Determine how many candles fit
        candle_width = 3  # wick-body-wick columns
        spacing = 1
        max_candles = max(1, (width - 6) // (candle_width + spacing))
        if n > max_candles:
            data = data[-max_candles:]
            n = len(data)

        all_highs = [d["high"] for d in data]
        all_lows = [d["low"] for d in data]
        price_max = max(all_highs)
        price_min = min(all_lows)
        price_range = price_max - price_min
        if price_range == 0:
            price_range = 1.0

        def _y(price: float) -> int:
            return int((price - price_min) / price_range * (height - 1))

        lines: list[str] = []
        # Build grid
        grid = [[" "] * (n * (candle_width + spacing)) for _ in range(height)]

        for i, d in enumerate(data):
            o, h, l, c = d["open"], d["high"], d["low"], d["close"]
            col = i * (candle_width + spacing) + 1
            yo, yh, yl, yc = _y(o), _y(h), _y(l), _y(c)
            color = _GREEN if c >= o else _RED
            body_top = max(yo, yc)
            body_bot = min(yo, yc)

            for row in range(height):
                if row == yh or row == yl:
                    grid[row][col + 1] = f"{color}│{_RESET}"
                if body_bot <= row <= body_top:
                    grid[row][col + 1] = f"{color}┃{_RESET}"
                elif yl <= row <= yh:
                    grid[row][col + 1] = f"{color}│{_RESET}"

        # Render top-to-bottom
        for row in reversed(range(height)):
            price_label = f"{price_min + (row / (height - 1)) * price_range:>8.2f}"
            line_str = "".join(grid[row])
            lines.append(f"{price_label} │{line_str}")

        # X-axis
        axis = " " * 9 + "└" + "─" * (n * (candle_width + spacing))
        lines.append(axis)
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Line chart (braille)
    # ------------------------------------------------------------------
    @staticmethod
    def line(
        values: list,
        width: int = 80,
        height: int = 15,
        label: str = "",
    ) -> str:
        """Render a braille-dot line chart."""
        if not values:
            return "(no data)"

        n = len(values)
        v_min = min(values)
        v_max = max(values)
        v_range = v_max - v_min
        if v_range == 0:
            v_range = 1.0

        # Braille: each cell is 2×4 dots → char_height = height*4, char_width = width*2
        chart_w = min(width - 10, 140)
        chart_h = height

        # Map values to row positions (0 = bottom)
        def _row(v: float) -> int:
            return int((v - v_min) / v_range * (chart_h * 4 - 1))

        # Braille offset table: dots are numbered
        # (0,0)=1  (1,0)=2  (2,0)=4  (3,0)=64
        # (0,1)=8  (1,1)=16 (2,1)=32 (3,1)=128
        BRAILLE_BASE = 0x2800
        DOT_MAP = {
            (0, 0): 0x01, (1, 0): 0x02, (2, 0): 0x04, (3, 0): 0x40,
            (0, 1): 0x08, (1, 1): 0x10, (2, 1): 0x20, (3, 1): 0x80,
        }

        # Create braille grid
        cols = chart_w
        rows = chart_h
        grid = [[0] * cols for _ in range(rows)]

        # Resample values to fit chart_w * 2 x-positions
        x_positions = chart_w * 2
        for xi in range(x_positions):
            idx = int(xi / x_positions * n)
            idx = min(idx, n - 1)
            yr = _row(values[idx])
            cell_row = rows - 1 - yr // 4
            dot_row = yr % 4
            cell_col = xi // 2
            dot_col = xi % 2
            if 0 <= cell_row < rows and 0 <= cell_col < cols:
                grid[cell_row][cell_col] |= DOT_MAP.get((dot_row, dot_col), 0)

        lines: list[str] = []
        if label:
            lines.append(f"{_BOLD}{label}{_RESET}")

        for r in range(rows):
            price = v_max - (r / max(rows - 1, 1)) * v_range
            row_chars = "".join(chr(BRAILLE_BASE + grid[r][c]) for c in range(cols))
            lines.append(f"{price:>8.2f} │{row_chars}")

        axis = " " * 9 + "└" + "─" * cols
        lines.append(axis)
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Horizontal bar chart
    # ------------------------------------------------------------------
    @staticmethod
    def bar(labels: list, values: list, width: int = 60) -> str:
        """Render a horizontal bar chart using block elements."""
        if not labels or not values:
            return "(no data)"

        max_val = max(abs(v) for v in values) if values else 1
        if max_val == 0:
            max_val = 1
        max_label = max(len(str(l)) for l in labels)
        bar_width = width - max_label - 15

        lines: list[str] = []
        for label, val in zip(labels, values):
            bar_len = int(abs(val) / max_val * bar_width)
            color = _GREEN if val >= 0 else _RED
            bar_str = "█" * bar_len + "░" * (bar_width - bar_len)
            lines.append(
                f"{str(label):>{max_label}} │ {color}{bar_str}{_RESET} {val:>8.2f}"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Heatmap
    # ------------------------------------------------------------------
    @staticmethod
    def heatmap(
        matrix: list,
        labels_x: list,
        labels_y: list,
    ) -> str:
        """Render a correlation-style heatmap using colored blocks.

        *matrix* is a 2D list (rows × cols) of floats, typically -1..+1.
        """
        if not matrix or not matrix[0]:
            return "(no data)"

        rows = len(matrix)
        cols = len(matrix[0])

        # Flatten to find range
        flat = [v for row in matrix for v in row]
        v_min = min(flat)
        v_max = max(flat)
        v_range = v_max - v_min if v_max != v_min else 1.0

        def _color_block(v: float) -> str:
            norm = (v - v_min) / v_range  # 0..1
            idx = min(int(norm * (len(_HEAT_COLORS) - 1)), len(_HEAT_COLORS) - 1)
            block_idx = min(int(norm * len(_HEAT_BLOCKS)), len(_HEAT_BLOCKS) - 1)
            return f"{_HEAT_COLORS[idx]}{_HEAT_BLOCKS[block_idx]}{_HEAT_BLOCKS[block_idx]}{_RESET}"

        max_y_label = max((len(str(l)) for l in labels_y), default=0)
        lines: list[str] = []

        # Header
        header = " " * (max_y_label + 2)
        for lx in labels_x:
            header += f"{str(lx):>4}"[:4]
        lines.append(header)

        for r in range(rows):
            label = f"{str(labels_y[r]):>{max_y_label}}"
            row_str = " ".join(_color_block(matrix[r][c]) for c in range(cols))
            lines.append(f"{label} │{row_str}")

        # Legend
        lines.append(f"\n  {_HEAT_COLORS[0]}■{_RESET} {v_min:.2f}  →  {_HEAT_COLORS[-1]}■{_RESET} {v_max:.2f}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Histogram
    # ------------------------------------------------------------------
    @staticmethod
    def histogram(
        values: list,
        bins: int = 20,
        width: int = 60,
    ) -> str:
        """Render a distribution histogram."""
        if not values:
            return "(no data)"

        v_min = min(values)
        v_max = max(values)
        if v_min == v_max:
            return f"All values = {v_min}"

        bin_width = (v_max - v_min) / bins
        counts = [0] * bins
        for v in values:
            idx = min(int((v - v_min) / bin_width), bins - 1)
            counts[idx] += 1

        max_count = max(counts)
        if max_count == 0:
            max_count = 1
        bar_area = width - 20

        lines: list[str] = []
        lines.append(f"{_BOLD}Distribution (n={len(values)}){_RESET}")
        for i in range(bins):
            lo = v_min + i * bin_width
            hi = lo + bin_width
            bar_len = int(counts[i] / max_count * bar_area)
            lines.append(
                f"{lo:>8.3f}-{hi:<8.3f} │{'█' * bar_len} {counts[i]}"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Sparkline (compact inline chart)
    # ------------------------------------------------------------------
    @staticmethod
    def sparkline(values: list) -> str:
        """Return a single-line sparkline using braille/block characters."""
        if not values:
            return ""
        ticks = "▁▂▃▄▅▆▇█"
        v_min = min(values)
        v_max = max(values)
        v_range = v_max - v_min if v_max != v_min else 1.0
        return "".join(
            ticks[min(int((v - v_min) / v_range * (len(ticks) - 1)), len(ticks) - 1)]
            for v in values
        )
