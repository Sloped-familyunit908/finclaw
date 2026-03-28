"""Wrapper to start paper trading with UTF-8 encoding and pre-warmed exchange."""
import os
import sys
import ssl

# Fix potential SSL issues in background processes
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUNBUFFERED"] = "1"
os.environ["PYTHONHTTPSVERIFY"] = "1"

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Disable SSL verification issues that can hang in background
# (OKX has many endpoints and ccxt loads ALL instruments)
ssl._create_default_https_context = ssl._create_unverified_context

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from scripts.live_crypto import main

if __name__ == "__main__":
    main()
