#!/usr/bin/env python3
"""
AutoTrading Runner — Autonomous LLM-powered strategy research.
Private script — uses configured LLM to run the research loop.

Usage:
  python run_autotrading.py                    # Run with defaults
  python run_autotrading.py --max-rounds 100   # Limit rounds
  python run_autotrading.py --dry-run          # Test without LLM
"""
import os
import sys
import json
import time
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

# Load env config
def load_env(env_file="autotrading.env"):
    """Load configuration from env file."""
    config = {}
    env_path = Path(__file__).parent / env_file
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                config[key.strip()] = val.strip()
    return config


def call_llm(prompt: str, config: dict) -> str:
    """Call LLM via OpenAI-compatible API."""
    import urllib.request
    
    base_url = config.get("LLM_BASE_URL", "http://localhost:23333/api/openai/v1")
    model = config.get("LLM_MODEL", "claude-sonnet-4.6")
    api_key = config.get("LLM_API_KEY", "none")
    
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": "You are an autonomous trading strategy researcher. Respond with ONLY the modified Python code for strategy.py. No explanations, no markdown, just pure Python code."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 4000,
        "temperature": 0.7,
    }).encode()
    
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    
    try:
        resp = urllib.request.urlopen(req, timeout=120)
        data = json.loads(resp.read().decode())
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  LLM call failed: {e}")
        return ""


def run_backtest(autotrading_dir: str) -> dict:
    """Run evaluate.py and parse results."""
    try:
        result = subprocess.run(
            [sys.executable, "evaluate.py"],
            cwd=autotrading_dir,
            capture_output=True,
            text=True,
            timeout=300,
        )
        
        metrics = {}
        for line in result.stdout.splitlines():
            if ":" in line and not line.startswith("Loading") and not line.startswith("Running") and not line.startswith("Loaded"):
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip()
                try:
                    metrics[key] = float(val)
                except ValueError:
                    metrics[key] = val
        
        return metrics
    except subprocess.TimeoutExpired:
        return {"fitness": 0, "status": "timeout"}
    except Exception as e:
        return {"fitness": 0, "status": f"error: {e}"}


def main():
    parser = argparse.ArgumentParser(description="AutoTrading Runner")
    parser.add_argument("--max-rounds", type=int, default=999999)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    config = load_env()
    finclaw_dir = os.path.expandvars(config.get("FINCLAW_DIR", os.path.expanduser("~/finclaw")))
    autotrading_dir = os.path.join(finclaw_dir, "autotrading")
    strategy_file = os.path.join(autotrading_dir, "strategy.py")
    results_file = os.path.join(autotrading_dir, "results.tsv")
    
    print("=" * 60)
    print("  AutoTrading — Autonomous Strategy Research")
    print(f"  LLM: {config.get('LLM_MODEL', 'unknown')}")
    print(f"  Dir: {autotrading_dir}")
    print("=" * 60)
    
    # Run baseline
    print("\n[Baseline] Running current strategy...")
    baseline = run_backtest(autotrading_dir)
    best_fitness = baseline.get("fitness", 0)
    print(f"  Baseline fitness: {best_fitness}")
    
    # Research loop
    for round_num in range(1, args.max_rounds + 1):
        print(f"\n{'='*60}")
        print(f"  Round {round_num} | Best fitness: {best_fitness}")
        print(f"{'='*60}")
        
        # Read current strategy
        current_code = Path(strategy_file).read_text(encoding="utf-8")
        
        if args.dry_run:
            print("  [dry-run] Skipping LLM call")
            continue
        
        # Ask LLM to improve
        prompt = f"""Current strategy.py (fitness={best_fitness}):

```python
{current_code}
```

Previous results from results.tsv:
{Path(results_file).read_text(encoding='utf-8') if Path(results_file).exists() else 'No previous results'}

Improve this strategy to get a higher fitness score. Try ONE specific change.
Output ONLY the complete modified strategy.py code."""
        
        print("  Asking LLM for improvement...")
        new_code = call_llm(prompt, config)
        
        if not new_code or "def generate_signals" not in new_code:
            print("  LLM returned invalid code, skipping")
            continue
        
        # Clean LLM output (remove markdown if present)
        if "```python" in new_code:
            new_code = new_code.split("```python")[1].split("```")[0]
        elif "```" in new_code:
            new_code = new_code.split("```")[1].split("```")[0]
        
        # Save new strategy
        backup = current_code
        Path(strategy_file).write_text(new_code, encoding="utf-8")
        
        # Test it
        print("  Running backtest...")
        results = run_backtest(autotrading_dir)
        new_fitness = results.get("fitness", 0)
        
        # Evaluate
        status = "discard"
        if new_fitness > best_fitness and results.get("trades", 0) >= 20:
            status = "keep"
            best_fitness = new_fitness
            print(f"  IMPROVED! fitness {new_fitness} (was {best_fitness})")
        elif results.get("status") in ("timeout", "insufficient_trades") or "error" in str(results.get("status", "")):
            status = "crash"
            Path(strategy_file).write_text(backup, encoding="utf-8")
            print(f"  CRASH: {results.get('status')}")
        else:
            Path(strategy_file).write_text(backup, encoding="utf-8")
            print(f"  Discarded. fitness {new_fitness} <= {best_fitness}")
        
        # Log to TSV
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        log_line = f"{ts}\t{new_fitness}\t{results.get('annual_return', 0)}\t{results.get('max_drawdown', 0)}\t{results.get('sharpe', 0)}\t{results.get('win_rate', 0)}\t{results.get('trades', 0)}\t{status}\tround {round_num}\n"
        with open(results_file, "a", encoding="utf-8") as f:
            f.write(log_line)
        
        time.sleep(2)  # Brief pause


if __name__ == "__main__":
    main()
