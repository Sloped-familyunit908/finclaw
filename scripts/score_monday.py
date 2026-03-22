"""Score all A-share stocks using Gen 79 champion DNA and output TOP recommendations for Monday."""
import sys, json, os, math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["FINCLAW_SKIP_FUNDAMENTALS"] = "1"  # Skip BaoStock (weekend, no API)

from src.evolution.auto_evolve import (
    AutoEvolver,
    StrategyDNA,
    score_stock,
    compute_rsi,
    compute_macd,
    compute_bollinger_bands,
    compute_kdj,
    compute_obv_trend,
    compute_volume_ratio,
    compute_ma_alignment,
    compute_atr,
    compute_aroon,
    compute_williams_r,
    compute_cci,
    compute_mfi,
    compute_donchian_position,
    compute_roc,
    compute_linear_regression,
    compute_price_volume_corr,
    filter_stock_pool,
)


def main():
    # Load specific gen DNA
    with open("evolution_results/gen_0199.json") as f:
        gen_data = json.load(f)

    dna_dict = gen_data["results"][0]["dna"]
    dna = StrategyDNA.from_dict(dna_dict)

    print(f"=== V4 Gen {gen_data['generation']} Champion DNA ===")
    print(f"min_score={dna.min_score}, hold_days={dna.hold_days}, max_positions={dna.max_positions}")
    print(f"stop_loss={dna.stop_loss_pct:.1f}%, take_profit={dna.take_profit_pct:.1f}%")
    print(f"rsi_buy={dna.rsi_buy_threshold}, rsi_sell={dna.rsi_sell_threshold:.1f}")
    print()

    # Load ALL stock data
    evolver = AutoEvolver(data_dir="data/a_shares", population_size=1, elite_count=1)
    data = evolver.load_data()
    print(f"Total stocks loaded: {len(data)}")

    # Filter stock pool
    data = filter_stock_pool(data)
    print(f"After filtering (no ST/banks/low liquidity): {len(data)}")
    print()

    # Score every stock at the LAST available date (2026-03-20, Friday)
    scored = []
    errors = 0
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

        idx = min_len - 1  # last trading day

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
                "rsi": rsi,
                "r2": r2,
                "slope": slope,
                "volume_ratio": vol_ratio,
                "close": closes,
                "open": opens,
                "high": highs_list,
                "low": lows_list,
                "volume": vols,
                "macd_line": macd_line,
                "macd_signal": macd_signal,
                "macd_hist": macd_hist,
                "bb_upper": bb_upper,
                "bb_middle": bb_middle,
                "bb_lower": bb_lower,
                "kdj_k": kdj_k,
                "kdj_d": kdj_d,
                "kdj_j": kdj_j,
                "obv_trend": obv,
                "ma_alignment": ma_align,
                "atr_pct": atr_pct,
                "roc": roc_vals,
                "williams_r": williams_r,
                "cci": cci,
                "mfi": mfi,
                "donchian_pos": donchian_pos,
                "aroon": aroon,
                "pv_corr": pv_corr,
                "fundamentals": {},  # No fundamental data on weekend
            }

            s = score_stock(idx, indicators, dna)
        except Exception as e:
            errors += 1
            continue

        # Collect info for display
        dates = sd.get("date", [])
        last_date = dates[min_len - 1] if dates and len(dates) >= min_len else "?"
        last_close = closes[idx]
        last_rsi = rsi[idx] if idx < len(rsi) and not math.isnan(rsi[idx]) else None
        last_kdj_j = kdj_j[idx] if idx < len(kdj_j) and not math.isnan(kdj_j[idx]) else None

        bb_pos = None
        if idx < len(bb_lower) and not math.isnan(bb_lower[idx]) and not math.isnan(bb_upper[idx]):
            bb_range = bb_upper[idx] - bb_lower[idx]
            if bb_range > 0:
                bb_pos = (closes[idx] - bb_lower[idx]) / bb_range

        vr = vol_ratio[idx] if idx < len(vol_ratio) and not math.isnan(vol_ratio[idx]) else None

        scored.append({
            "code": code,
            "score": round(s, 3),
            "price": round(last_close, 2),
            "date": last_date,
            "rsi": round(last_rsi, 1) if last_rsi is not None else None,
            "kdj_j": round(last_kdj_j, 1) if last_kdj_j is not None else None,
            "bb_pos": round(bb_pos, 3) if bb_pos is not None else None,
            "vol_ratio": round(vr, 2) if vr is not None else None,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)

    print(f"Scored {len(scored)} stocks (errors: {errors})")
    print()

    # Show results
    passed = [s for s in scored if s["score"] >= dna.min_score]
    print(f"*** Stocks passing min_score >= {dna.min_score}: {len(passed)} ***")
    print()

    print(f"{'Rank':<5} {'Code':<15} {'Score':<8} {'Price':<10} {'RSI':<8} {'KDJ-J':<8} {'BB%':<8} {'VolR':<8}")
    print("=" * 80)

    show = passed[:30] if passed else scored[:20]
    for i, s in enumerate(show):
        rsi_s = f"{s['rsi']}" if s['rsi'] is not None else "-"
        kdj_s = f"{s['kdj_j']}" if s['kdj_j'] is not None else "-"
        bb_s = f"{s['bb_pos']}" if s['bb_pos'] is not None else "-"
        vr_s = f"{s['vol_ratio']}" if s['vol_ratio'] is not None else "-"
        marker = " <<<BUY" if s['score'] >= dna.min_score else ""
        print(f"{i+1:<5} {s['code']:<15} {s['score']:<8} {s['price']:<10} {rsi_s:<8} {kdj_s:<8} {bb_s:<8} {vr_s:<8}{marker}")

    # Save
    output = {
        "gen": 79,
        "dna_summary": {
            "hold_days": dna.hold_days,
            "stop_loss_pct": dna.stop_loss_pct,
            "take_profit_pct": dna.take_profit_pct,
            "max_positions": dna.max_positions,
            "min_score": dna.min_score,
        },
        "scored_date": scored[0]["date"] if scored else "",
        "total_scored": len(scored),
        "passed_threshold": len(passed),
        "top30": scored[:30],
    }
    with open("evolution_results/monday_picks.json", "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nSaved to evolution_results/monday_picks.json")


if __name__ == "__main__":
    main()
