#!/usr/bin/env python3
"""
record_demo.py — Generate a static terminal demo output for FinClaw README.

Runs key demo commands and saves the output as:
  - demo_output.txt  (plain text, ready for README code block)
  - demo_output.svg  (SVG terminal screenshot for embedding)

Usage:
    python scripts/record_demo.py
"""

import subprocess
import sys
import os
import html
from datetime import datetime

COMMANDS = [
    ("finclaw demo", "python -m src.cli demo"),
    ("finclaw quote AAPL", "python -m src.cli quote AAPL"),
    ("finclaw quote BTC/USDT", "python -m src.cli quote BTC/USDT"),
]

# SVG template — a clean dark terminal look
SVG_TEMPLATE = """\
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <style>
    .bg {{ fill: #1e1e2e; }}
    .title-bar {{ fill: #313244; }}
    .btn-close {{ fill: #f38ba8; }}
    .btn-min {{ fill: #f9e2af; }}
    .btn-max {{ fill: #a6e3a1; }}
    .title {{ fill: #cdd6f4; font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', monospace; font-size: 13px; }}
    .prompt {{ fill: #89b4fa; font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', monospace; font-size: 13px; }}
    .output {{ fill: #cdd6f4; font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', monospace; font-size: 13px; white-space: pre; }}
  </style>
  <!-- Background -->
  <rect class="bg" width="{width}" height="{height}" rx="8"/>
  <!-- Title bar -->
  <rect class="title-bar" width="{width}" height="36" rx="8"/>
  <rect class="title-bar" y="28" width="{width}" height="8"/>
  <circle class="btn-close" cx="20" cy="18" r="6"/>
  <circle class="btn-min" cx="40" cy="18" r="6"/>
  <circle class="btn-max" cx="60" cy="18" r="6"/>
  <text class="title" x="{title_x}" y="22" text-anchor="middle">FinClaw Demo</text>
  <!-- Content -->
{content}
</svg>
"""

def run_command(display_cmd, actual_cmd):
    """Run a command and capture output."""
    try:
        result = subprocess.run(
            actual_cmd.split(),
            capture_output=True,
            timeout=30,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        return (result.stdout + result.stderr).decode("utf-8", errors="replace")
    except Exception as e:
        return f"[Error running {display_cmd}: {e}]"


def generate_txt(outputs):
    """Generate plain text demo output."""
    lines = []
    for display_cmd, output in outputs:
        lines.append(f"$ {display_cmd}")
        lines.append(output.rstrip())
        lines.append("")
    return "\n".join(lines)


def generate_svg(text, width=820):
    """Generate SVG terminal screenshot from text."""
    lines = text.split("\n")
    line_height = 18
    padding_top = 50
    padding_bottom = 20
    padding_left = 16
    height = padding_top + len(lines) * line_height + padding_bottom

    content_parts = []
    for i, line in enumerate(lines):
        y = padding_top + i * line_height
        escaped = html.escape(line)
        # Highlight prompt lines
        css_class = "prompt" if line.startswith("$") else "output"
        content_parts.append(
            f'  <text class="{css_class}" x="{padding_left}" y="{y}">{escaped}</text>'
        )

    content = "\n".join(content_parts)
    return SVG_TEMPLATE.format(
        width=width,
        height=height,
        title_x=width // 2,
        content=content,
    )


def main():
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    print("Recording FinClaw demo output...")
    
    outputs = []
    for display_cmd, actual_cmd in COMMANDS:
        print(f"  Running: {display_cmd}")
        output = run_command(display_cmd, actual_cmd)
        outputs.append((display_cmd, output))
    
    # Generate text output
    txt = generate_txt(outputs)
    
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
    os.makedirs(out_dir, exist_ok=True)
    
    txt_path = os.path.join(out_dir, "demo_output.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(txt)
    print(f"  Text saved: {txt_path}")
    
    # Generate SVG
    svg = generate_svg(txt)
    svg_path = os.path.join(out_dir, "demo_output.svg")
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"  SVG saved: {svg_path}")
    
    print(f"\nTotal lines: {len(txt.splitlines())}")
    print("Done! Use assets/demo_output.svg in your README.")


if __name__ == "__main__":
    main()
