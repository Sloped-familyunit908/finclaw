"""
Honest Backtest — runs the FIXED crypto backtest engine on existing best DNA.
"""
import json, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["FINCLAW_SKIP_FUNDAMENTALS"] = "1"

print("Starting...", flush=True)

from src.evolution.auto_evolve import (
    StrategyDNA,
    compute_rsi, compute_linear_regression, compute_volume_ratio,
    compute_macd, compute_bollinger_bands, compute_kdj, compute_obv_trend,
    compute_ma_alignment, compute_atr, compute_roc, compute_williams_r,
    compute_cci, compute_mfi, compute_donchian_position, compute_aroon,
    compute_price_volume_corr, score_stock
)
from src.evolution.crypto_backtest import CryptoBacktestEngine

print("Imports done", flush=True)

# Load best DNA
best_path = os.path.join(os.path.dirname(__file__), "..", "evolution_results", "best_ever.json")
with open(best_path, "r") as f:
    result = json.load(f)

dna = StrategyDNA()
for k, v in result["dna"].items():
    if hasattr(dna, k):
        setattr(dna, k, v)
    elif isinstance(dna.custom_weights, dict):
        dna.custom_weights[k] = v

print(f"DNA loaded (gen {result['generation']})", flush=True)
print(f"OLD claimed: annual={result['annual_return']:.2f}% sharpe={result['sharpe']:.2f}", flush=True)

# Load data
from src.evolution.data_loader import UnifiedDataLoader
loader = UnifiedDataLoader()
data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "crypto")
data = loader.load_csv_dir(data_dir, market="crypto", min_days=60, clean=True)
codes = list(data.keys())
print(f"Loaded {len(codes)} assets", flush=True)

# Compute indicators
print("Computing indicators...", flush=True)
indicators = {}
for code in codes:
    sd = data[code]
    c = sd["close"]; v = sd["volume"]; o = sd["open"]; h = sd["high"]; l = sd["low"]
    ml = min(len(c), len(v), len(o), len(h), len(l))
    c, v, o, h, l = c[:ml], v[:ml], o[:ml], h[:ml], l[:ml]
    sd["close"], sd["volume"], sd["open"], sd["high"], sd["low"] = c, v, o, h, l

    indicators[code] = {
        "rsi": compute_rsi(c), "r2": compute_linear_regression(c)[0],
        "slope": compute_linear_regression(c)[1],
        "volume_ratio": compute_volume_ratio(v),
        "close": c, "open": o, "high": h, "low": l, "volume": v,
        "macd_line": compute_macd(c)[0], "macd_signal": compute_macd(c)[1],
        "macd_hist": compute_macd(c)[2],
        "bb_upper": compute_bollinger_bands(c)[0], "bb_middle": compute_bollinger_bands(c)[1],
        "bb_lower": compute_bollinger_bands(c)[2],
        "kdj_k": compute_kdj(h, l, c)[0], "kdj_d": compute_kdj(h, l, c)[1],
        "kdj_j": compute_kdj(h, l, c)[2],
        "obv_trend": compute_obv_trend(c, v), "ma_alignment": compute_ma_alignment(c),
        "atr_pct": compute_atr(h, l, c), "roc": compute_roc(c),
        "williams_r": compute_williams_r(h, l, c),
        "cci": compute_cci(c, h, l), "mfi": compute_mfi(h, l, c, v),
        "donchian_pos": compute_donchian_position(h, l, c),
        "aroon": compute_aroon(c), "pv_corr": compute_price_volume_corr(c, v),
    }

print("Indicators done", flush=True)

# Load factors
try:
    from src.evolution.factor_discovery import FactorRegistry, create_seed_factors
    create_seed_factors("factors")
    fr = FactorRegistry("factors")
    fr.load_all()
    fcount = len(fr.list_factors())
    for code in codes:
        active = {}
        if dna.custom_weights:
            for fname, w in dna.custom_weights.items():
                if w >= 0.001 and fname in fr.factors:
                    active[fname] = fr.factors[fname].compute_fn
        indicators[code]["_factor_fns"] = active
    print(f"Factors: {fcount} total, {len(active)} active", flush=True)
except Exception as e:
    print(f"Factors skipped: {e}", flush=True)

# Date range
first_code = codes[0]
total_periods = len(data[first_code]["close"])
warmup = 30
train_end = warmup + int((total_periods - warmup) * 0.7)
val_start = train_end
val_end = total_periods

print(f"Periods: {total_periods}, train={warmup}-{train_end}, val={val_start}-{val_end}", flush=True)

# Run FIXED engine
engine = CryptoBacktestEngine()

for label, ds, de in [("FULL", warmup, val_end), ("VAL", val_start, val_end), ("TRAIN", warmup, train_end)]:
    print(f"\nRunning {label} backtest ({ds}->{de})...", flush=True)
    r = engine.run_backtest(dna, data, indicators, codes, ds, de)
    ann, dd, wr, sh, cal, trades, pf, sort, mcl, mr, mc, at = r

    periods_used = de - ds
    days = periods_used / 24.0
    years = days / 365.0

    print(f"--- {label} ({days:.0f}d / {years:.2f}y) ---", flush=True)
    print(f"  Annual Return:  {ann:.2f}%", flush=True)
    print(f"  Max Drawdown:   {dd:.2f}%", flush=True)
    print(f"  Sharpe:         {sh:.2f}", flush=True)
    print(f"  Sortino:        {sort:.2f}", flush=True)
    print(f"  Win Rate:       {wr:.2f}%", flush=True)
    print(f"  Total Trades:   {trades}", flush=True)
    print(f"  Profit Factor:  {pf:.2f}", flush=True)
    print(f"  Calmar:         {cal:.2f}", flush=True)

print("\nDone!", flush=True)
