"""
Ensemble Strategy Scoring
Combines multiple evolved DNA strategies for more stable stock picks.
"""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["FINCLAW_SKIP_FUNDAMENTALS"] = "1"

from pathlib import Path
from src.evolution.auto_evolve import (
    AutoEvolver, StrategyDNA,
    score_stock, compute_rsi, compute_macd, compute_bollinger_bands,
    compute_kdj, compute_obv_trend, compute_volume_ratio, compute_ma_alignment,
    compute_atr, compute_aroon, compute_williams_r, compute_cci, compute_mfi,
    compute_donchian_position, compute_roc, compute_linear_regression,
    compute_price_volume_corr, filter_stock_pool,
)

def load_all_dna(best_dir="evolution_results/best_dna"):
    """Load all saved best DNA strategies with their fitness."""
    dnas = []
    for fp in Path(best_dir).glob("*.json"):
        if fp.name.startswith("_"):
            continue
        try:
            with open(fp) as f:
                data = json.load(f)
            dna_dict = data["results"][0]["dna"]
            dna = StrategyDNA.from_dict(dna_dict)
            fitness = data["results"][0].get("fitness", 1.0)
            annual = data["results"][0].get("annual_return", 0)
            gen = data.get("generation", 0)
            dnas.append({
                "dna": dna,
                "fitness": fitness,
                "annual": annual,
                "gen": gen,
                "file": fp.name,
            })
        except Exception as e:
            print(f"  Skipped {fp.name}: {e}")
    return dnas

def score_all_stocks(dna, data, evolver):
    """Score all stocks using a single DNA. Returns dict of code -> score."""
    scores = {}
    for code, sd in data.items():
        closes = sd["close"]
        vols = sd["volume"]
        opens = sd["open"]
        highs_list = sd["high"]
        lows_list = sd["low"]
        
        min_len = min(len(closes), len(vols), len(opens), len(highs_list), len(lows_list))
        if min_len < 60:
            continue
        
        closes = closes[:min_len]
        vols = vols[:min_len]
        opens = opens[:min_len]
        highs_list = highs_list[:min_len]
        lows_list = lows_list[:min_len]
        idx = min_len - 1
        
        try:
            rsi = compute_rsi(closes)
            r2, slope = compute_linear_regression(closes)
            vol_ratio = compute_volume_ratio(vols)
            macd_line, macd_signal, macd_hist = compute_macd(closes)
            bb_upper, bb_middle, bb_lower, bb_width = compute_bollinger_bands(closes)
            kdj_k, kdj_d, kdj_j = compute_kdj(highs_list, lows_list, closes)
            obv = compute_obv_trend(closes, vols)
            ma_align = compute_ma_alignment(closes)
            atr_pct = compute_atr(highs_list, lows_list, closes)
            roc_vals = compute_roc(closes)
            williams_r = compute_williams_r(highs_list, lows_list, closes)
            cci = compute_cci(closes, highs_list, lows_list)
            mfi = compute_mfi(highs_list, lows_list, closes, vols)
            donchian_pos = compute_donchian_position(highs_list, lows_list, closes)
            aroon = compute_aroon(closes)
            pv_corr = compute_price_volume_corr(closes, vols)
            
            indicators = {
                "rsi": rsi, "r2": r2, "slope": slope, "volume_ratio": vol_ratio,
                "close": closes, "open": opens, "high": highs_list,
                "low": lows_list, "volume": vols,
                "macd_line": macd_line, "macd_signal": macd_signal, "macd_hist": macd_hist,
                "bb_upper": bb_upper, "bb_middle": bb_middle, "bb_lower": bb_lower,
                "kdj_k": kdj_k, "kdj_d": kdj_d, "kdj_j": kdj_j,
                "obv_trend": obv, "ma_alignment": ma_align,
                "atr_pct": atr_pct, "roc": roc_vals, "williams_r": williams_r,
                "cci": cci, "mfi": mfi, "donchian_pos": donchian_pos,
                "aroon": aroon, "pv_corr": pv_corr,
                "fundamentals": {},
                "_factor_fns": {},  # No dynamic factors for speed
            }
            
            s = score_stock(idx, indicators, dna)
            scores[code] = s
        except Exception:
            continue
    
    return scores


def ensemble_score(dnas, data, evolver):
    """Compute ensemble scores across multiple DNA strategies."""
    all_scores = {}  # code -> [(score, weight)]
    
    # Normalize fitness as weights
    total_fitness = sum(d["fitness"] for d in dnas)
    if total_fitness <= 0:
        total_fitness = 1.0
    
    print(f"Running ensemble with {len(dnas)} strategies...")
    
    for i, dna_info in enumerate(dnas):
        weight = dna_info["fitness"] / total_fitness
        print(f"  Strategy {i+1}: Gen {dna_info['gen']}, annual={dna_info['annual']:.0f}%, fitness={dna_info['fitness']:.0f}, weight={weight:.2f}")
        
        scores = score_all_stocks(dna_info["dna"], data, evolver)
        
        for code, score in scores.items():
            if code not in all_scores:
                all_scores[code] = []
            all_scores[code].append((score, weight))
    
    # Compute weighted average + consensus bonus
    final_scores = []
    for code, sw_list in all_scores.items():
        weighted_sum = sum(s * w for s, w in sw_list)
        total_weight = sum(w for _, w in sw_list)
        avg_score = weighted_sum / total_weight if total_weight > 0 else 0
        
        # Consensus bonus: if stock appears in top 20 of multiple strategies, boost it
        # Count how many strategies ranked it highly (score > 5.0)
        high_count = sum(1 for s, _ in sw_list if s >= 5.0)
        consensus = high_count / len(dnas)  # 0 to 1
        
        # Final = weighted avg + 10% consensus bonus
        final = avg_score * (1.0 + consensus * 0.1)
        
        # Get price for display
        sd = data.get(code, {})
        closes = sd.get("close", [])
        price = closes[-1] if closes else 0
        
        # Get RSI
        rsi_val = None
        if len(closes) >= 20:
            rsi = compute_rsi(closes)
            if len(rsi) > 0 and not math.isnan(rsi[-1]):
                rsi_val = round(rsi[-1], 1)
        
        final_scores.append({
            "code": code,
            "ensemble_score": round(final, 3),
            "avg_score": round(avg_score, 3),
            "consensus": round(consensus, 2),
            "high_count": high_count,
            "price": round(price, 2),
            "rsi": rsi_val,
        })
    
    final_scores.sort(key=lambda x: x["ensemble_score"], reverse=True)
    return final_scores


def main():
    # Load DNA strategies
    dnas = load_all_dna()
    if not dnas:
        print("No DNA backups found in evolution_results/best_dna/")
        # Try loading latest
        if os.path.exists("evolution_results/latest.json"):
            with open("evolution_results/latest.json") as f:
                data = json.load(f)
            dna = StrategyDNA.from_dict(data["results"][0]["dna"])
            dnas = [{"dna": dna, "fitness": data["results"][0].get("fitness", 1), "annual": data["results"][0].get("annual_return", 0), "gen": data.get("generation", 0), "file": "latest.json"}]
    
    print(f"Loaded {len(dnas)} DNA strategies")
    
    # Load stock data
    evolver = AutoEvolver(data_dir="data/a_shares", population_size=1, elite_count=1)
    data = evolver.load_data(quality_filter=True, max_stocks=500)
    print(f"Loaded {len(data)} stocks")
    
    # Run ensemble
    results = ensemble_score(dnas, data, evolver)
    
    # Display top 20
    print(f"\n{'Rank':<5} {'Code':<15} {'Ensemble':<10} {'Avg':<8} {'Consensus':<10} {'#High':<6} {'Price':<10} {'RSI':<8}")
    print("=" * 80)
    for i, r in enumerate(results[:20]):
        rsi_s = str(r["rsi"]) if r["rsi"] else "-"
        print(f"{i+1:<5} {r['code']:<15} {r['ensemble_score']:<10} {r['avg_score']:<8} {r['consensus']:<10} {r['high_count']:<6} {r['price']:<10} {rsi_s:<8}")
    
    # Save
    output = {
        "type": "ensemble",
        "strategies_used": len(dnas),
        "top20": results[:20],
        "total_scored": len(results),
    }
    with open("evolution_results/ensemble_picks.json", "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to evolution_results/ensemble_picks.json")


if __name__ == "__main__":
    main()
