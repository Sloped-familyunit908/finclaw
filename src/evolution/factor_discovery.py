"""
Factor Discovery Engine — LLM-guided factor creation for the evolution engine.

Architecture:
  1. Each "factor" is a small Python function: (closes, highs, lows, volumes, idx) -> float [0, 1]
  2. Factors are stored as .py files in factors/ directory
  3. The evolution engine loads all factors dynamically
  4. LLM proposes new factors based on performance feedback
  5. New factors get added to the weight vector and evolved

This module handles:
  - Dynamic factor loading
  - Factor validation (must be safe, deterministic, fast)
  - Factor performance tracking
  - LLM-based factor proposal (via prompt templates)
"""

import os
import math
import importlib.util
import traceback
from pathlib import Path
from typing import Dict, List, Any, Callable, Optional, Tuple
from dataclasses import dataclass, field


# ============================================================
# Factor Registry
# ============================================================

@dataclass
class FactorMeta:
    """Metadata for a registered factor."""
    name: str
    description: str
    source_file: str
    compute_fn: Callable  # (closes, highs, lows, volumes, idx) -> float [0,1]
    category: str = "custom"  # technical, fundamental, sentiment, custom
    version: int = 1
    avg_score: float = 0.0  # tracking
    times_selected: int = 0  # how often evolution gave it non-zero weight


class FactorRegistry:
    """Dynamic factor registry — loads factors from directory."""

    def __init__(self, factors_dir: str = "factors"):
        self.factors_dir = Path(factors_dir)
        self.factors: Dict[str, FactorMeta] = {}
        self._builtin_loaded = False

    def load_all(self) -> int:
        """Load all factor files from factors/ directory.
        
        Each .py file should define:
          - FACTOR_NAME: str
          - FACTOR_DESC: str  
          - FACTOR_CATEGORY: str (optional, default 'custom')
          - compute(closes, highs, lows, volumes, idx) -> float
        
        Returns number of factors loaded.
        """
        if not self.factors_dir.exists():
            self.factors_dir.mkdir(parents=True, exist_ok=True)
            return 0

        count = 0
        for fp in sorted(self.factors_dir.glob("*.py")):
            if fp.name.startswith("_"):
                continue
            try:
                factor = self._load_factor_file(fp)
                if factor:
                    self.factors[factor.name] = factor
                    count += 1
            except Exception as e:
                print(f"  [factor] failed to load {fp.name}: {e}")

        return count

    def _load_factor_file(self, path: Path) -> Optional[FactorMeta]:
        """Load a single factor from a .py file."""
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if not spec or not spec.loader:
            return None

        module = importlib.util.module_from_spec(spec)
        
        # Provide safe builtins
        module.__builtins__ = {
            'math': math,
            'abs': abs, 'min': min, 'max': max, 'sum': sum,
            'len': len, 'range': range, 'enumerate': enumerate,
            'float': float, 'int': int, 'bool': bool,
            'zip': zip, 'map': map, 'filter': filter,
            'sorted': sorted, 'reversed': reversed,
            'round': round, 'pow': pow,
            'True': True, 'False': False, 'None': None,
            'isinstance': isinstance, 'type': type,
            'list': list, 'tuple': tuple, 'dict': dict,
            'ValueError': ValueError, 'TypeError': TypeError,
            'ZeroDivisionError': ZeroDivisionError,
            'IndexError': IndexError,
            '__import__': __import__,
            'print': print,
        }

        spec.loader.exec_module(module)

        name = getattr(module, 'FACTOR_NAME', path.stem)
        desc = getattr(module, 'FACTOR_DESC', 'No description')
        category = getattr(module, 'FACTOR_CATEGORY', 'custom')
        compute_fn = getattr(module, 'compute', None)

        if compute_fn is None:
            return None

        # Validate: must return float in [0, 1] for a simple test
        try:
            test_closes = [10.0 + i * 0.1 for i in range(100)]
            test_highs = [c + 0.5 for c in test_closes]
            test_lows = [c - 0.5 for c in test_closes]
            test_vols = [1000000.0] * 100
            result = compute_fn(test_closes, test_highs, test_lows, test_vols, 99)
            if not isinstance(result, (int, float)):
                print(f"  [factor] {name}: compute() returned {type(result)}, expected float")
                return None
            if math.isnan(result) or math.isinf(result):
                print(f"  [factor] {name}: compute() returned {result}")
                return None
        except Exception as e:
            print(f"  [factor] {name}: validation failed: {e}")
            return None

        return FactorMeta(
            name=name,
            description=desc,
            source_file=str(path),
            compute_fn=compute_fn,
            category=category,
        )

    def compute_all(self, closes: list, highs: list, lows: list, 
                    volumes: list, idx: int) -> Dict[str, float]:
        """Compute all registered factors for a given stock at a given day.
        
        Returns dict of factor_name -> score [0, 1].
        """
        results = {}
        for name, factor in self.factors.items():
            try:
                val = factor.compute_fn(closes, highs, lows, volumes, idx)
                # Clamp to [0, 1]
                val = max(0.0, min(1.0, float(val)))
                results[name] = val
            except Exception:
                results[name] = 0.5  # neutral on error
        return results

    def list_factors(self) -> List[str]:
        """Return list of factor names."""
        return list(self.factors.keys())


# ============================================================
# LLM Factor Proposal Templates
# ============================================================

FACTOR_PROPOSAL_PROMPT = """You are a quantitative finance researcher. Your task is to invent a NEW trading factor (alpha signal) for A-share (Chinese stock market) trading.

## Current factors already in use:
{existing_factors}

## Recent evolution results:
- Best annual return: {best_return}%
- Best Sharpe: {best_sharpe}
- Current strategy style: {strategy_style}

## Performance feedback:
{performance_feedback}

## Your task:
Create ONE new factor that could improve the strategy. The factor should:
1. Be DIFFERENT from existing factors (don't just re-implement RSI or MACD)
2. Use only price, volume, high, low data (no external API calls)
3. Return a value between 0.0 (bearish) and 1.0 (bullish)
4. Be computationally fast (no loops over full history per call)
5. Have a clear financial intuition

## Output format:
Write a complete Python file with this structure:

```python
FACTOR_NAME = "your_factor_name"  # lowercase, no spaces
FACTOR_DESC = "One-line description of what this factor measures"
FACTOR_CATEGORY = "technical"  # or "momentum", "mean_reversion", "volatility", "microstructure"

def compute(closes, highs, lows, volumes, idx):
    \"\"\"
    Compute factor value at index idx.
    
    Args:
        closes: list of closing prices (full history)
        highs: list of high prices
        lows: list of low prices  
        volumes: list of volumes
        idx: current day index to compute for
        
    Returns:
        float in [0.0, 1.0] where 1.0 = most bullish
    \"\"\"
    # Your implementation here
    return 0.5
```

## Ideas to consider:
- Volume-weighted price acceleration
- Intraday range contraction/expansion patterns
- Price symmetry around moving averages
- Consecutive up/down day patterns with volume confirmation
- Gap analysis (open vs previous close)
- Relative volume at price extremes
- Volatility regime shifts
- Price-volume divergence patterns
- Order flow imbalance proxies
- Mean reversion speed indicators

Be creative! The evolution engine will determine the optimal weight for your factor.
"""

FACTOR_FILE_TEMPLATE = '''"""
Auto-generated factor: {name}
Description: {description}
Category: {category}
Generated: {timestamp}
"""

FACTOR_NAME = "{name}"
FACTOR_DESC = "{description}"
FACTOR_CATEGORY = "{category}"


def compute(closes, highs, lows, volumes, idx):
    """{description}"""
{code}
'''


# ============================================================
# Seed Factors — Good starting factors that demonstrate the pattern
# ============================================================

SEED_FACTORS = {
    "gap_momentum": {
        "desc": "Gap-up/gap-down momentum — measures if stock opened above/below previous close",
        "category": "momentum",
        "code": """
    if idx < 1:
        return 0.5
    
    # Gap = (today's open - yesterday's close) / yesterday's close
    prev_close = closes[idx - 1]
    if prev_close <= 0:
        return 0.5
    
    # We don't have opens directly, approximate from close/high/low
    # Use (high + low) / 2 as rough open proxy
    today_mid = (highs[idx] + lows[idx]) / 2.0
    gap_pct = (today_mid - prev_close) / prev_close
    
    # Normalize: -3% to +3% maps to 0.0 to 1.0
    score = (gap_pct + 0.03) / 0.06
    return max(0.0, min(1.0, score))
""",
    },
    "volume_acceleration": {
        "desc": "Volume acceleration — is volume growing faster than recently?",
        "category": "microstructure",
        "code": """
    if idx < 10:
        return 0.5
    
    # Recent 5-day average volume
    vol_5 = sum(volumes[idx-4:idx+1]) / 5.0
    # Previous 5-day average (days -10 to -5)
    vol_prev5 = sum(volumes[idx-9:idx-4]) / 5.0
    
    if vol_prev5 <= 0:
        return 0.5
    
    accel = vol_5 / vol_prev5 - 1.0
    # -50% to +100% maps to 0 to 1
    score = (accel + 0.5) / 1.5
    return max(0.0, min(1.0, score))
""",
    },
    "range_contraction": {
        "desc": "Range contraction — narrowing daily range often precedes breakout",
        "category": "volatility",
        "code": """
    if idx < 20:
        return 0.5
    
    # Average True Range ratio: recent 5 day vs 20 day
    def true_range(i):
        if i < 1:
            return highs[i] - lows[i]
        return max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
    
    atr_5 = sum(true_range(idx - j) for j in range(5)) / 5.0
    atr_20 = sum(true_range(idx - j) for j in range(20)) / 20.0
    
    if atr_20 <= 0:
        return 0.5
    
    ratio = atr_5 / atr_20
    # Contraction (ratio < 1) is bullish (breakout coming)
    # ratio 0.3 -> score 1.0, ratio 1.5 -> score 0.0
    score = 1.0 - (ratio - 0.3) / 1.2
    return max(0.0, min(1.0, score))
""",
    },
    "smart_money_divergence": {
        "desc": "Smart money divergence — price falling but big-volume bars are buying",
        "category": "microstructure",
        "code": """
    if idx < 20:
        return 0.5
    
    # Look at last 20 days
    # Find "big volume" days (above average)
    lookback = min(20, idx)
    avg_vol = sum(volumes[idx - lookback + 1:idx + 1]) / lookback
    
    if avg_vol <= 0:
        return 0.5
    
    # On big-volume days, what's the average price change?
    big_vol_changes = []
    normal_changes = []
    for i in range(idx - lookback + 1, idx + 1):
        if i < 1:
            continue
        change = (closes[i] - closes[i-1]) / closes[i-1] if closes[i-1] > 0 else 0
        if volumes[i] > avg_vol * 1.5:
            big_vol_changes.append(change)
        else:
            normal_changes.append(change)
    
    if not big_vol_changes or not normal_changes:
        return 0.5
    
    # Divergence: big-volume-day returns vs normal-day returns
    big_avg = sum(big_vol_changes) / len(big_vol_changes)
    normal_avg = sum(normal_changes) / len(normal_changes)
    
    # If big volume days are positive but normal days negative = smart money buying
    divergence = big_avg - normal_avg
    # -2% to +2% maps to 0 to 1
    score = (divergence + 0.02) / 0.04
    return max(0.0, min(1.0, score))
""",
    },
    "price_efficiency": {
        "desc": "Price efficiency ratio — straight-line distance vs actual path, measures trend clarity",
        "category": "momentum",
        "code": """
    if idx < 10:
        return 0.5
    
    lookback = min(10, idx)
    
    # Net price change (straight line)
    net_change = abs(closes[idx] - closes[idx - lookback])
    
    # Total path length (sum of absolute daily changes)
    total_path = 0.0
    for i in range(idx - lookback + 1, idx + 1):
        total_path += abs(closes[i] - closes[i - 1])
    
    if total_path <= 0:
        return 0.5
    
    # Efficiency = net / total, ranges from 0 (choppy) to 1 (straight line)
    efficiency = net_change / total_path
    
    # Direction bonus: upward trend is bullish
    if closes[idx] > closes[idx - lookback]:
        score = 0.5 + efficiency * 0.5  # 0.5 to 1.0
    else:
        score = 0.5 - efficiency * 0.5  # 0.0 to 0.5
    
    return max(0.0, min(1.0, score))
""",
    },
    "consecutive_pattern": {
        "desc": "Consecutive up/down days with volume pattern — 3+ down days with declining volume = bullish reversal setup",
        "category": "mean_reversion",
        "code": """
    if idx < 5:
        return 0.5
    
    # Count consecutive down days
    down_days = 0
    vol_declining = True
    for i in range(idx, max(idx - 10, 0), -1):
        if i < 1:
            break
        if closes[i] < closes[i-1]:
            down_days += 1
            if i > 1 and volumes[i] > volumes[i-1]:
                vol_declining = False
        else:
            break
    
    # Count consecutive up days
    up_days = 0
    for i in range(idx, max(idx - 10, 0), -1):
        if i < 1:
            break
        if closes[i] > closes[i-1]:
            up_days += 1
        else:
            break
    
    # 3+ down days with declining volume = reversal setup (bullish)
    if down_days >= 3 and vol_declining:
        score = min(0.7 + down_days * 0.05, 1.0)
    elif down_days >= 3:
        score = 0.6
    elif up_days >= 3:
        score = 0.3  # extended up, less bullish
    else:
        score = 0.5
    
    return max(0.0, min(1.0, score))
""",
    },
}


def create_seed_factors(factors_dir: str = "factors"):
    """Create seed factor files if they don't exist."""
    path = Path(factors_dir)
    path.mkdir(parents=True, exist_ok=True)
    
    created = 0
    for name, info in SEED_FACTORS.items():
        fp = path / f"{name}.py"
        if not fp.exists():
            content = FACTOR_FILE_TEMPLATE.format(
                name=name,
                description=info["desc"],
                category=info["category"],
                timestamp="seed",
                code=info["code"],
            )
            fp.write_text(content, encoding="utf-8")
            created += 1
    
    return created


if __name__ == "__main__":
    # Test: create seeds and load
    n = create_seed_factors()
    print(f"Created {n} seed factors")
    
    registry = FactorRegistry()
    loaded = registry.load_all()
    print(f"Loaded {loaded} factors: {registry.list_factors()}")
    
    # Test compute
    closes = [10.0 + i * 0.05 + (i % 7) * 0.2 for i in range(100)]
    highs = [c + 0.5 for c in closes]
    lows = [c - 0.3 for c in closes]
    vols = [1000000 + (i % 5) * 200000 for i in range(100)]
    
    results = registry.compute_all(closes, highs, lows, vols, 99)
    print(f"\nFactor scores at idx=99:")
    for name, score in sorted(results.items()):
        print(f"  {name}: {score:.3f}")
