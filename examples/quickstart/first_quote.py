"""
FinClaw Quickstart: Get Your First Quote
=========================================
Just 5 lines to get a real-time stock quote.

Usage:
    python first_quote.py
"""

from finclaw_ai import FinClaw

fc = FinClaw()
quote = fc.quote("AAPL")
print(f"AAPL: ${quote['price']:.2f} ({quote['change_pct']:+.2f}%)")
