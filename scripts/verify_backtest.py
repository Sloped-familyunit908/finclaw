"""
Backtest Verification Script
============================
Replays the crypto backtester trade-by-trade with verbose logging
to verify the claimed 25,000%+ returns.
"""

import json
import math
import os
import sys
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["FINCLAW_SKIP_FUNDAMENTALS"] = "1"  # Skip baostock

from src.evolution.auto_evolve import AutoEvolver, score_stock, StrategyDNA
from src.evolution.crypto_backtest import CryptoBacktestEngine


def load_best_dna():
    """Load the best DNA from evolution results."""
    path = os.path.join(os.path.dirname(__file__), "..", "evolution_results", "best_ever.json")
    with open(path, "r") as f:
        result = json.load(f)
    return result


def main():
    # Load DNA
    result = load_best_dna()
    dna_dict = result["dna"]
    print(f"=== BACKTEST VERIFICATION ===")
    print(f"Generation: {result['generation']}")
    print(f"Claimed annual return: {result['annual_return']:.2f}%")
    print(f"Claimed total trades: {result['total_trades']}")
    print(f"Claimed win rate: {result['win_rate']:.2f}%")
    print(f"Claimed max drawdown: {result['max_drawdown']:.2f}%")
    print()

    # Reconstruct DNA
    dna = StrategyDNA()
    for k, v in dna_dict.items():
        if hasattr(dna, k):
            setattr(dna, k, v)
        elif hasattr(dna, 'custom_weights') and isinstance(dna.custom_weights, dict):
            dna.custom_weights[k] = v

    print(f"DNA params: hold_days={dna.hold_days}, max_positions={dna.max_positions}")
    print(f"  stop_loss={dna.stop_loss_pct:.2f}%, take_profit={dna.take_profit_pct:.2f}%")
    print(f"  min_score={dna.min_score}")
    print()

    # Load data using the same data loader
    from src.evolution.data_loader import UnifiedDataLoader
    loader = UnifiedDataLoader()
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "crypto")
    data = loader.load_csv_dir(data_dir, market="crypto", min_days=60, clean=True)
    codes = list(data.keys())
    print(f"Loaded {len(codes)} assets: {codes}")

    # Check data timestamps
    for code in codes[:2]:
        sd = data[code]
        dates = sd.get("date", sd.get("dates", []))
        if dates:
            print(f"  {code}: {len(sd['close'])} periods, {dates[0]} -> {dates[-1]}")
        else:
            print(f"  {code}: {len(sd['close'])} periods (no date column)")
    print()

    # Compute indicators (same as evolver)
    from src.evolution.auto_evolve import (
        compute_rsi, compute_linear_regression, compute_volume_ratio,
        compute_macd, compute_bollinger_bands, compute_kdj, compute_obv_trend,
        compute_ma_alignment, compute_atr, compute_roc, compute_williams_r,
        compute_cci, compute_mfi, compute_donchian_position, compute_aroon,
        compute_price_volume_corr
    )

    indicators = {}
    for code in codes:
        sd = data[code]
        closes = sd["close"]
        vols = sd["volume"]
        opens = sd["open"]
        highs_list = sd["high"]
        lows_list = sd["low"]

        min_len = min(len(closes), len(vols), len(opens), len(highs_list), len(lows_list))
        closes = closes[:min_len]
        vols = vols[:min_len]
        opens = opens[:min_len]
        highs_list = highs_list[:min_len]
        lows_list = lows_list[:min_len]

        # Update data dict with trimmed arrays
        sd["close"] = closes
        sd["volume"] = vols
        sd["open"] = opens
        sd["high"] = highs_list
        sd["low"] = lows_list

        rsi = compute_rsi(closes)
        r2, slope = compute_linear_regression(closes)
        vol_ratio = compute_volume_ratio(vols)
        macd_line, macd_signal, macd_hist = compute_macd(closes)
        bb_upper, bb_middle, bb_lower, bb_width = compute_bollinger_bands(closes)
        kdj_k, kdj_d, kdj_j = compute_kdj(highs_list, lows_list, closes)
        obv = compute_obv_trend(closes, vols)
        ma_align = compute_ma_alignment(closes)
        atr_pct = compute_atr(highs_list, lows_list, closes)
        roc_arr = compute_roc(closes)
        will_r = compute_williams_r(highs_list, lows_list, closes)
        cci_arr = compute_cci(closes, highs_list, lows_list)
        mfi_arr = compute_mfi(highs_list, lows_list, closes, vols)
        donch = compute_donchian_position(highs_list, lows_list, closes)
        aroon_arr = compute_aroon(closes)
        pv_corr = compute_price_volume_corr(closes, vols)

        indicators[code] = {
            "rsi": rsi, "r2": r2, "slope": slope, "volume_ratio": vol_ratio,
            "close": closes, "open": opens, "high": highs_list, "low": lows_list,
            "volume": vols,
            "macd_line": macd_line, "macd_signal": macd_signal, "macd_hist": macd_hist,
            "bb_upper": bb_upper, "bb_middle": bb_middle, "bb_lower": bb_lower,
            "kdj_k": kdj_k, "kdj_d": kdj_d, "kdj_j": kdj_j,
            "obv_trend": obv, "ma_alignment": ma_align,
            "atr_pct": atr_pct, "roc": roc_arr, "williams_r": will_r,
            "cci": cci_arr, "mfi": mfi_arr, "donchian_pos": donch,
            "aroon": aroon_arr, "pv_corr": pv_corr,
        }

    # Load factor registry for custom weights (89% of scoring weight!)
    try:
        from src.evolution.factor_discovery import FactorRegistry
        fr = FactorRegistry("factors")
        fr.load_all()
        factor_count = len(fr.list_factors())
        print(f"  [factors] Loaded {factor_count} factors from registry")
        for code in codes:
            if fr and fr.factors:
                active_factors = {}
                if hasattr(dna, 'custom_weights') and dna.custom_weights:
                    for fname, w in dna.custom_weights.items():
                        if w >= 0.001 and fname in fr.factors:
                            active_factors[fname] = fr.factors[fname].compute_fn
                indicators[code]["_factor_fns"] = active_factors
                print(f"  [factors] {code}: {len(active_factors)} active factors")
    except Exception as e:
        print(f"  [factors] WARNING: Could not load factor registry: {e}")
        print(f"  [factors] This means 89% of scoring weight is MISSING!")
        print(f"  [factors] Custom factor weights sum to 0.8937 vs standard 0.1089")

    # â”€â”€ Determine date range (same as evolver: warmup=30, 70/30 split) â”€â”€
    first_code = codes[0]
    total_periods = len(data[first_code]["close"])
    warmup = 30
    train_end = warmup + int((total_periods - warmup) * 0.7)
    val_start = train_end
    val_end = total_periods

    # The evolver computes fitness using VALIDATION set
    # Let's run on BOTH train and validation to compare
    print(f"Total periods: {total_periods}")
    print(f"Training: period {warmup} â†’ {train_end} ({train_end - warmup} periods)")
    print(f"Validation: period {val_start} â†’ {val_end} ({val_end - val_start} periods)")
    print()

    # Try to get dates for period mapping
    dates = data[first_code].get("date", data[first_code].get("dates", []))

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # RUN VERBOSE BACKTEST ON VALIDATION SET
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    engine = CryptoBacktestEngine()  # leverage=1, fee_taker=0.0004

    initial_capital = 1_000_000.0
    capital = initial_capital
    hold_periods = max(1, dna.hold_days)  # = 2

    all_trades = []
    total_fees = 0.0
    peak_capital = capital
    max_dd = 0.0
    capital_curve = [(val_start, capital)]

    trade_num = 0
    period = val_start

    while period < val_end - hold_periods:
        # Score all assets
        scored = []
        for code in codes:
            sd = data[code]
            if period >= len(sd["close"]):
                continue
            ind = indicators[code]
            s = score_stock(period, ind, dna)
            if s >= dna.min_score:
                scored.append((code, s, False))

        scored.sort(key=lambda x: x[1], reverse=True)
        picks = scored[:dna.max_positions]

        if picks:
            per_pos = capital / len(picks)

            for code, _score, is_short in picks:
                sd = data[code]
                entry_period = period
                if entry_period >= len(sd["close"]):
                    continue

                entry_price = sd["open"][entry_period]
                if entry_price <= 0:
                    continue

                shares = per_pos / entry_price
                exit_price = entry_price
                actual_exit_period = entry_period
                exit_reason = "hold_expire"

                for d in range(entry_period, min(entry_period + hold_periods, len(sd["close"]))):
                    low = sd["low"][d]
                    high = sd["high"][d]
                    close = sd["close"][d]

                    # Stop loss
                    sl_price = entry_price * (1 - dna.stop_loss_pct / 100)
                    if low <= sl_price:
                        exit_price = sl_price
                        actual_exit_period = d
                        exit_reason = "stop_loss"
                        break

                    # Take profit
                    tp_price = entry_price * (1 + dna.take_profit_pct / 100)
                    if high >= tp_price:
                        exit_price = tp_price
                        actual_exit_period = d
                        exit_reason = "take_profit"
                        break

                    exit_price = close
                    actual_exit_period = d

                # Compute PnL
                trade_return, pnl = engine._compute_pnl(
                    entry_price, exit_price, shares, is_short,
                    entry_period, actual_exit_period, False,
                )

                # Track fees
                entry_fee = entry_price * shares * engine.fee_taker
                exit_fee = exit_price * shares * engine.fee_taker
                total_fees += entry_fee + exit_fee

                capital += pnl
                trade_num += 1

                # Dates
                entry_date = dates[entry_period] if entry_period < len(dates) else f"period_{entry_period}"
                exit_date = dates[actual_exit_period] if actual_exit_period < len(dates) else f"period_{actual_exit_period}"

                trade_info = {
                    "num": trade_num,
                    "code": code,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "entry_date": str(entry_date),
                    "exit_date": str(exit_date),
                    "pnl": pnl,
                    "pnl_pct": trade_return,
                    "capital_after": capital,
                    "position_size": per_pos,
                    "shares": shares,
                    "exit_reason": exit_reason,
                    "score": _score,
                }
                all_trades.append(trade_info)

                # Print first 50 trades and every 500th after
                if trade_num <= 50 or trade_num % 500 == 0:
                    direction = "SHORT" if is_short else "LONG"
                    sign = "+" if pnl > 0 else ""
                    print(
                        f"Trade #{trade_num:>4d}: {direction} {code:>10s} @ ${entry_price:>10.2f} "
                        f"({entry_date}) â†’ ${exit_price:>10.2f} ({exit_date}) "
                        f"| PnL: {sign}${pnl:>12.2f} ({sign}{trade_return:>6.2f}%) "
                        f"| Capital: ${capital:>15.2f} | Size: ${per_pos:>12.2f} "
                        f"| Exit: {exit_reason} | Score: {_score:.2f}"
                    )

        # Update drawdown
        if capital > peak_capital:
            peak_capital = capital
        dd = (peak_capital - capital) / peak_capital * 100 if peak_capital > 0 else 0
        if dd > max_dd:
            max_dd = dd

        capital_curve.append((period, capital))
        period += hold_periods

    # â”€â”€ Summary Statistics â”€â”€
    print("\n" + "=" * 80)
    print("BACKTEST SUMMARY (Validation Set)")
    print("=" * 80)

    total_return_pct = (capital - initial_capital) / initial_capital * 100
    val_periods = val_end - val_start
    val_hours = val_periods  # 1 period = 1 hour
    val_days = val_hours / 24
    val_years = val_days / 365

    if total_return_pct > -100:
        annual_return = ((capital / initial_capital) ** (1 / max(val_years, 0.01)) - 1) * 100
    else:
        annual_return = -100

    wins = sum(1 for t in all_trades if t["pnl"] > 0)
    losses = sum(1 for t in all_trades if t["pnl"] <= 0)
    win_rate = wins / len(all_trades) * 100 if all_trades else 0
    avg_pnl_pct = sum(t["pnl_pct"] for t in all_trades) / len(all_trades) if all_trades else 0

    # Largest gain/loss
    if all_trades:
        best_trade = max(all_trades, key=lambda t: t["pnl"])
        worst_trade = min(all_trades, key=lambda t: t["pnl"])
    else:
        best_trade = worst_trade = {"pnl": 0, "pnl_pct": 0, "code": "N/A"}

    avg_win_pnl = sum(t["pnl_pct"] for t in all_trades if t["pnl"] > 0) / max(wins, 1)
    avg_loss_pnl = sum(t["pnl_pct"] for t in all_trades if t["pnl"] <= 0) / max(losses, 1)

    # Exit reason breakdown
    exit_reasons = {}
    for t in all_trades:
        r = t["exit_reason"]
        exit_reasons[r] = exit_reasons.get(r, 0) + 1

    print(f"Initial capital:      ${initial_capital:>15,.2f}")
    print(f"Final capital:        ${capital:>15,.2f}")
    print(f"Total return:         {total_return_pct:>10.2f}%")
    print(f"Annualized return:    {annual_return:>10.2f}%")
    print(f"Max drawdown:         {max_dd:>10.2f}%")
    print(f"Total trades:         {len(all_trades):>10d}")
    print(f"Win rate:             {win_rate:>10.2f}% ({wins}W / {losses}L)")
    print(f"Avg trade P&L:        {avg_pnl_pct:>10.4f}%")
    print(f"Avg win P&L:          {avg_win_pnl:>10.4f}%")
    print(f"Avg loss P&L:         {avg_loss_pnl:>10.4f}%")
    print(f"Total fees paid:      ${total_fees:>15,.2f}")
    print(f"Best trade:           +${best_trade['pnl']:>12,.2f} ({best_trade['pnl_pct']:.2f}%) {best_trade['code']}")
    print(f"Worst trade:          -${abs(worst_trade['pnl']):>12,.2f} ({worst_trade['pnl_pct']:.2f}%) {worst_trade['code']}")
    print(f"Validation days:      {val_days:.1f} days ({val_years:.2f} years)")
    print(f"Trades per month:     {len(all_trades) / (val_days/30):.1f}")
    print(f"Exit reasons:         {exit_reasons}")
    print()

    # â”€â”€ BUG ANALYSIS â”€â”€
    print("=" * 80)
    print("BUG ANALYSIS")
    print("=" * 80)

    # 1. Look-ahead bias check
    print("\n1. LOOK-AHEAD BIAS:")
    print("   score_stock(period=t) uses indicators[t] (including close[t], high[t], low[t])")
    print("   BUT entry is at open[t] â€” which occurs BEFORE close/high/low of period t are known.")
    print("   âš  THIS IS LOOK-AHEAD BIAS!")
    print("   The scoring function sees the candle's close, high, low before the candle completes,")
    print("   then enters at the OPEN of that same candle.")
    print("   Fix: score should use period t-1 data, enter at open[t]")
    print()

    # 2. Same-candle stop/take-profit check
    print("2. SAME-CANDLE STOP/TAKE-PROFIT:")
    entry_candle_exits = sum(1 for t in all_trades
                             if t["exit_reason"] in ("stop_loss", "take_profit")
                             and t["entry_date"] == t["exit_date"])
    print(f"   Trades exited on entry candle: {entry_candle_exits} / {len(all_trades)}")
    print("   The stop/take loop starts from entry_period (same candle as entry).")
    print("   With entry at open[t], checking low[t]/high[t] is valid but aggressive.")
    print()

    # 3. Compounding analysis
    print("3. COMPOUNDING EFFECT:")
    if all_trades:
        # Find capital at various points
        milestones = [100, 500, 1000, 2000, 3000]
        for m in milestones:
            if m <= len(all_trades):
                cap = all_trades[m-1]["capital_after"]
                pos_size = all_trades[m-1]["position_size"]
                print(f"   After trade #{m}: capital=${cap:,.2f}, position_size=${pos_size:,.2f}")
        print("   Capital is FULLY reinvested each period (no position size capping).")
        print("   This creates exponential growth when win_rate Ã— avg_win > (1-win_rate) Ã— avg_loss.")
    print()

    # 4. Data snooping
    print("4. DATA SNOOPING / OVERFITTING:")
    print("   The DNA was evolved over 69 generations using the TRAINING set.")
    print(f"   Training: periods {warmup}-{train_end} ({train_end-warmup} periods)")
    print(f"   Validation: periods {val_start}-{val_end} ({val_end-val_start} periods)")
    print("   Walk-forward split exists (70/30), which is good.")
    print("   BUT: the strategy has hundreds of parameters (200+ custom weights).")
    print("   With this many degrees of freedom, even the validation set can be overfit")
    print("   through evolutionary selection pressure across generations.")
    print()

    # 5. Position sizing reality check
    print("5. POSITION SIZING REALITY:")
    if all_trades:
        max_pos_size = max(t["position_size"] for t in all_trades)
        min_pos_size = min(t["position_size"] for t in all_trades)
        print(f"   Smallest position: ${min_pos_size:,.2f}")
        print(f"   Largest position:  ${max_pos_size:,.2f}")
        print("   In real markets, orders of $500K+ in altcoins would cause")
        print("   significant slippage. No slippage is modeled.")
    print()

    # 6. Score distribution at trade entries
    print("6. SCORE DISTRIBUTION:")
    if all_trades:
        scores = [t["score"] for t in all_trades]
        avg_score = sum(scores) / len(scores)
        min_s = min(scores)
        max_s = max(scores)
        print(f"   Avg entry score: {avg_score:.4f} (min={min_s:.4f}, max={max_s:.4f})")
        print(f"   min_score threshold: {dna.min_score}")
    print()

    # â”€â”€ Write output file â”€â”€
    output_path = os.path.join(os.path.dirname(__file__), "..", "..", "backtest-verification.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Backtest Verification Report\n\n")
        f.write(f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n")
        f.write(f"**DNA Generation:** {result['generation']}\n")
        f.write(f"**Claimed Annual Return:** {result['annual_return']:.2f}%\n")
        f.write(f"**Claimed Win Rate:** {result['win_rate']:.2f}%\n\n")

        f.write("## Summary (Validation Set)\n\n")
        f.write(f"| Metric | Value |\n|---|---|\n")
        f.write(f"| Initial Capital | ${initial_capital:,.2f} |\n")
        f.write(f"| Final Capital | ${capital:,.2f} |\n")
        f.write(f"| Total Return | {total_return_pct:.2f}% |\n")
        f.write(f"| Annualized Return | {annual_return:.2f}% |\n")
        f.write(f"| Max Drawdown | {max_dd:.2f}% |\n")
        f.write(f"| Total Trades | {len(all_trades)} |\n")
        f.write(f"| Win Rate | {win_rate:.2f}% ({wins}W / {losses}L) |\n")
        f.write(f"| Avg Trade P&L | {avg_pnl_pct:.4f}% |\n")
        f.write(f"| Total Fees | ${total_fees:,.2f} |\n")
        f.write(f"| Validation Period | {val_days:.0f} days ({val_years:.2f} years) |\n")
        f.write(f"| Trades/Month | {len(all_trades)/(val_days/30):.1f} |\n")
        f.write(f"| Exit Reasons | {exit_reasons} |\n\n")

        f.write("## First 20 Trades\n\n")
        f.write("| # | Asset | Entry Price | Entry Date | Exit Price | Exit Date | P&L | P&L% | Capital After | Exit Reason |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|\n")
        for t in all_trades[:20]:
            sign = "+" if t["pnl"] > 0 else ""
            f.write(f"| {t['num']} | {t['code']} | ${t['entry_price']:,.2f} | {t['entry_date']} | "
                    f"${t['exit_price']:,.2f} | {t['exit_date']} | {sign}${t['pnl']:,.2f} | "
                    f"{sign}{t['pnl_pct']:.2f}% | ${t['capital_after']:,.2f} | {t['exit_reason']} |\n")

        f.write("\n## Capital Curve Milestones\n\n")
        f.write("| Trade # | Capital | Position Size |\n|---|---|---|\n")
        for m in [1, 100, 500, 1000, 2000, 3000, 4000, 5000, len(all_trades)]:
            if 0 < m <= len(all_trades):
                t = all_trades[m-1]
                f.write(f"| {m} | ${t['capital_after']:,.2f} | ${t['position_size']:,.2f} |\n")

        f.write("\n## Bug Analysis\n\n")
        f.write("### ðŸ”´ BUG 1: Look-Ahead Bias (CRITICAL)\n\n")
        f.write("`score_stock(period=t)` reads indicators at index `t`, which includes `close[t]`, `high[t]`, `low[t]`.\n")
        f.write("But entry is at `open[t]` â€” which happens BEFORE the candle's high/low/close are known.\n\n")
        f.write("**Impact:** The scoring function can see whether the current candle went up or down,\n")
        f.write("then retroactively decide to enter at the open. This is the single biggest source of\n")
        f.write("inflated returns.\n\n")
        f.write("**Fix:** Score should use `period t-1` indicators, enter at `open[t]`.\n\n")

        f.write("### ðŸŸ¡ BUG 2: Unrestricted Compounding\n\n")
        f.write("Capital is fully reinvested: `per_pos = capital / len(picks)`.\n")
        f.write("After $1M â†’ $5M, each position is $2.5M. This causes exponential growth.\n\n")
        f.write("**Impact:** Even small per-trade edges compound into astronomical returns.\n")
        f.write("Real trading would cap position sizes or use Kelly criterion.\n\n")

        f.write("### ðŸŸ¡ BUG 3: No Slippage Modeling\n\n")
        f.write("Large positions (potentially millions of dollars) are filled at exact open/SL/TP prices.\n")
        f.write("In real crypto markets, a $500K+ market order would cause 0.1-1% slippage on most altcoins.\n\n")

        f.write("### ðŸŸ¡ BUG 4: Overfitting Risk (200+ Parameters)\n\n")
        f.write("The DNA has 200+ tunable weights evolved over 69 generations.\n")
        f.write("Even with a 70/30 train/val split, this many parameters can overfit through\n")
        f.write("evolutionary selection pressure.\n\n")

        f.write("### â„¹ï¸ Not a Bug: Same-Candle SL/TP\n\n")
        f.write(f"Trades exited on entry candle: {entry_candle_exits}/{len(all_trades)}.\n")
        f.write("Entry at open, then checking high/low of same candle for SL/TP is valid\n")
        f.write("(intra-candle price movement), though it's optimistic on order fill.\n\n")

        f.write("## Assessment\n\n")
        f.write("**The 25,000% annual return is inflated, primarily due to look-ahead bias.**\n\n")
        f.write("The scoring function sees the current period's close/high/low before entering at the open.\n")
        f.write("This is equivalent to knowing the future â€” the strategy can see if a candle will go up\n")
        f.write("before deciding to buy at the candle's opening price.\n\n")
        f.write("Combined with full compounding and no slippage, even a small look-ahead edge\n")
        f.write("compounds into absurd returns over thousands of trades.\n\n")

        f.write("## Recommendations\n\n")
        f.write("1. **Fix look-ahead bias:** Score at period `t-1`, enter at `open[t]`\n")
        f.write("2. **Cap position sizes:** Use Kelly criterion or max 2% of capital per trade\n")
        f.write("3. **Add slippage model:** At least 0.05% for BTC/ETH, 0.1-0.5% for altcoins\n")
        f.write("4. **Reduce parameter count:** Prune weights below 0.005 to reduce overfitting\n")
        f.write("5. **True out-of-sample test:** Hold out the last 3-6 months entirely from evolution\n")
        f.write("6. **Paper trade validation:** Run forward on live data for at least 1 month\n")

    print(f"\nReport written to: {os.path.abspath(output_path)}")


if __name__ == "__main__":
    main()

