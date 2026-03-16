"""
FinClaw: REST API Usage
========================
Use FinClaw's built-in REST API for integrations.

Start the server:
    finclaw api --port 8000

Then run this script to interact with it:
    python rest_server.py
"""

import requests

BASE_URL = "http://localhost:8000/api/v1"


def get_quote(symbol: str) -> dict:
    """Get a real-time quote."""
    resp = requests.get(f"{BASE_URL}/quote/{symbol}")
    resp.raise_for_status()
    return resp.json()


def screen_stocks(params: dict) -> list:
    """Screen stocks with filters."""
    resp = requests.post(f"{BASE_URL}/screen", json=params)
    resp.raise_for_status()
    return resp.json()["results"]


def run_backtest(config: dict) -> dict:
    """Run a backtest."""
    resp = requests.post(f"{BASE_URL}/backtest", json=config)
    resp.raise_for_status()
    return resp.json()


# --- Demo ---
if __name__ == "__main__":
    # 1. Get a quote
    quote = get_quote("AAPL")
    print(f"AAPL: ${quote['price']:.2f}")

    # 2. Screen stocks
    results = screen_stocks({
        "pe_ratio_max": 25,
        "market_cap_min": 1_000_000_000,
        "sort_by": "volume",
        "limit": 5,
    })
    print(f"\nTop 5 by volume:")
    for s in results:
        print(f"  {s['symbol']}: ${s['price']:.2f}")

    # 3. Run a backtest
    bt = run_backtest({
        "symbol": "MSFT",
        "strategy": "sma_crossover",
        "params": {"fast_period": 10, "slow_period": 30},
        "start": "2024-01-01",
        "end": "2024-12-31",
    })
    print(f"\nBacktest: {bt['total_return']:+.2f}% return, {bt['sharpe_ratio']:.2f} Sharpe")
