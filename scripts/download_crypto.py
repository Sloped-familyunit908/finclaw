"""
Download 1h OHLCV data for top 20 cryptocurrencies using ccxt.
Tries multiple exchanges: OKX, Bybit, then Binance.
Saves to data/crypto/ directory, one CSV per pair.
"""

import os
import sys
import time
import csv
from datetime import datetime, timezone, timedelta

try:
    import ccxt
except ImportError:
    print("ERROR: ccxt is not installed.")
    print("Install it with:")
    print("  pip install ccxt")
    print("  or: python -m pip install ccxt")
    sys.exit(1)


# Top 20 crypto pairs
SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
    "ADA/USDT", "DOGE/USDT", "AVAX/USDT", "DOT/USDT", "LINK/USDT",
    "MATIC/USDT", "UNI/USDT", "ATOM/USDT", "LTC/USDT", "FIL/USDT",
    "APT/USDT", "ARB/USDT", "OP/USDT", "NEAR/USDT", "SUI/USDT",
]

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "crypto")
TIMEFRAME = "1h"
LIMIT_PER_REQUEST = 100  # Conservative for all exchanges
RATE_LIMIT_SLEEP = 1.0  # seconds between requests

# Exchanges to try in order (OKX and Bybit accessible from China)
EXCHANGE_CONFIGS = [
    ("okx", {"enableRateLimit": True}),
    ("bybit", {"enableRateLimit": True}),
    ("binance", {"enableRateLimit": True, "options": {"defaultType": "spot"}}),
]


def symbol_to_filename(symbol: str) -> str:
    """Convert 'BTC/USDT' to 'BTCUSDT.csv'."""
    return symbol.replace("/", "") + ".csv"


def create_exchange():
    """Try to connect to exchanges in order, return the first working one."""
    for name, config in EXCHANGE_CONFIGS:
        try:
            print(f"Trying {name}...", end=" ", flush=True)
            exchange_class = getattr(ccxt, name)
            exchange = exchange_class(config)
            # Test connection
            exchange.load_markets()
            print(f"OK - Connected to {name}")
            return exchange, name
        except Exception as e:
            print(f"FAIL - {e}")
            continue
    
    print("ERROR: Could not connect to any exchange.")
    sys.exit(1)


def download_symbol(exchange, symbol: str, since_ms: int, until_ms: int) -> list:
    """Download all 1h OHLCV data for a symbol from since_ms to until_ms."""
    all_candles = []
    current_since = since_ms
    retries = 0
    max_retries = 3
    
    while current_since < until_ms:
        try:
            candles = exchange.fetch_ohlcv(
                symbol,
                timeframe=TIMEFRAME,
                since=current_since,
                limit=LIMIT_PER_REQUEST,
            )
            retries = 0  # Reset on success
        except ccxt.BadSymbol as e:
            print(f"\n    Symbol {symbol} not available: {e}")
            return []
        except (ccxt.NetworkError, ccxt.ExchangeNotAvailable) as e:
            retries += 1
            if retries > max_retries:
                print(f"\n    Max retries exceeded for {symbol}: {e}")
                return all_candles
            print(f"\n    Network error, retry {retries}/{max_retries}...", end="", flush=True)
            time.sleep(5 * retries)
            continue
        except ccxt.ExchangeError as e:
            print(f"\n    Exchange error for {symbol}: {e}")
            return all_candles
        except Exception as e:
            retries += 1
            if retries > max_retries:
                print(f"\n    Unexpected error for {symbol}: {e}")
                return all_candles
            time.sleep(3)
            continue

        if not candles:
            break

        # Filter out candles beyond until_ms
        for c in candles:
            if c[0] <= until_ms:
                all_candles.append(c)

        # Move to next batch
        last_ts = candles[-1][0]
        if last_ts <= current_since:
            break  # No progress, avoid infinite loop
        current_since = last_ts + 1  # +1ms to avoid duplicate

        # Progress indicator
        if len(all_candles) % 500 == 0:
            print(".", end="", flush=True)

        time.sleep(RATE_LIMIT_SLEEP)

    return all_candles


def save_candles(candles: list, filepath: str):
    """Save candles to CSV with columns: date,open,high,low,close,volume."""
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "open", "high", "low", "close", "volume"])
        for c in candles:
            timestamp_ms = c[0]
            dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
            date_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            writer.writerow([date_str, c[1], c[2], c[3], c[4], c[5]])


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Connect to an exchange
    exchange, exchange_name = create_exchange()

    # 2 years of data
    now = datetime.now(tz=timezone.utc)
    since = now - timedelta(days=730)  # ~2 years
    since_ms = int(since.timestamp() * 1000)
    until_ms = int(now.timestamp() * 1000)

    print(f"\nDownloading {TIMEFRAME} data for {len(SYMBOLS)} crypto pairs from {exchange_name}")
    print(f"Period: {since.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}")
    print(f"Output: {OUTPUT_DIR}")
    print("=" * 60)

    success_count = 0
    for i, symbol in enumerate(SYMBOLS, 1):
        filename = symbol_to_filename(symbol)
        filepath = os.path.join(OUTPUT_DIR, filename)

        print(f"[{i}/{len(SYMBOLS)}] {symbol} ...", end=" ", flush=True)

        candles = download_symbol(exchange, symbol, since_ms, until_ms)

        if candles:
            save_candles(candles, filepath)
            print(f" OK {len(candles)} candles -> {filename}")
            success_count += 1
        else:
            print(f" SKIP - No data")

        # Extra sleep between symbols
        if i < len(SYMBOLS):
            time.sleep(1.5)

    print("=" * 60)
    print(f"Download complete! {success_count}/{len(SYMBOLS)} pairs downloaded.")

    # Summary
    total_files = len([f for f in os.listdir(OUTPUT_DIR) if f.endswith(".csv")])
    print(f"Total CSV files in {OUTPUT_DIR}: {total_files}")


if __name__ == "__main__":
    main()
