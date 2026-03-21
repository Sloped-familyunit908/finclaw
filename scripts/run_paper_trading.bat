@echo off
REM FinClaw Paper Trading Daily Run
REM Runs after market close to update paper trading portfolios

set PYTHONIOENCODING=utf-8
cd /d %~dp0\..
python scripts\paper_trading_daily.py >> logs\paper_trading.log 2>&1

REM Log timestamp
echo [%date% %time%] Paper trading daily run completed >> logs\paper_trading.log
