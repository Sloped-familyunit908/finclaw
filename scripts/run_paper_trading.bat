@echo off
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
cd /d C:\Users\kazhou\.openclaw\workspace\finclaw
python scripts/start_paper_trading.py --mode dry_run --exchange okx --symbols BTC/USDT ETH/USDT SOL/USDT ATOM/USDT DOT/USDT XRP/USDT ADA/USDT AVAX/USDT LINK/USDT UNI/USDT DOGE/USDT LTC/USDT FIL/USDT APT/USDT ARB/USDT OP/USDT >>logs\paper_trading_20260328.log 2>>logs\paper_trading_20260328_err.log
