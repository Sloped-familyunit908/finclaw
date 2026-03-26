@echo off
cd /d C:\Users\kazhou\.openclaw\workspace\finclaw
python -u scripts\run_evolution.py --market crypto --data-dir data/crypto --generations 999999 --population 30 --results-dir evolution_results_crypto
