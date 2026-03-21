@echo off
REM FinClaw Strategy Evolution Engine
REM Run this via Windows Task Scheduler for 24/7 evolution.
REM Results are saved to evolution_results/ and can resume on restart.

cd /d %~dp0\..
python scripts\run_evolution.py --generations 100 --save-interval 10
