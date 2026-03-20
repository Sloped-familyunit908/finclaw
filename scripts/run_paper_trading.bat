@echo off
REM FinClaw Paper Trading Daily Run
REM Runs after market close to update paper trading portfolios

set PYTHONIOENCODING=utf-8
cd /d C:\Users\kazhou\.openclaw\workspace\finclaw
"C:\Users\kazhou\AppData\Local\Programs\Python\Python312\python.exe" scripts\paper_trading_daily.py >> logs\paper_trading.log 2>&1

REM Log timestamp
echo [%date% %time%] Paper trading daily run completed >> logs\paper_trading.log
