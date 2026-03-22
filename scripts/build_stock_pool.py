"""
Build a curated A-share stock pool for evolution engine.
Focuses on AI/tech/growth sectors, removes trash.
Outputs a fixed stock list for stable evolution.
"""
import sys, os, json, io, statistics

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["FINCLAW_SKIP_FUNDAMENTALS"] = "1"

from src.evolution.auto_evolve import AutoEvolver
from pathlib import Path


def main():
    # Load ALL stocks (no filter)
    evolver = AutoEvolver(data_dir="data/a_shares", population_size=1, elite_count=1)
    data = evolver.load_data(quality_filter=False)
    print(f"Total stocks with data: {len(data)}")

    # === EXCLUSION RULES ===
    excluded = set()
    reasons = {}

    # Bank codes
    BANK_CODES = {
        "sh_601398", "sh_601288", "sh_601988", "sh_601939", "sh_601328",
        "sh_600036", "sh_601166", "sh_600016", "sh_600000", "sh_601818",
        "sh_600015", "sh_601998", "sh_600919", "sh_601009", "sh_601169",
        "sz_000001", "sz_002142", "sh_601838", "sh_600926", "sh_601077",
        "sh_600908", "sz_002839", "sz_002936", "sz_002948", "sh_601528",
        "sh_601860", "sz_002807", "sz_002966",
    }

    # Insurance/brokerage (low vol)
    INSURANCE_BROKER = {
        "sh_601318", "sh_601601", "sh_601628", "sh_601336",  # 保险
        "sh_601688", "sh_601211", "sh_600030", "sh_601066",  # 券商大盘
        "sh_600837", "sh_601377", "sh_601878", "sh_601881",
    }

    # Utility/highway/port (too stable, no alpha)
    BORING = {
        "sh_600900", "sh_600886", "sh_601985",  # 电力
    }

    for code in data:
        closes = data[code]["close"]
        volumes = data[code]["volume"]
        
        if len(closes) < 120:  # Need at least ~6 months of data
            excluded.add(code)
            reasons[code] = "too_short"
            continue

        last_close = closes[-1]
        
        # 1. Remove penny stocks
        if last_close < 5.0:
            excluded.add(code)
            reasons[code] = "penny"
            continue
        
        # 2. Remove banks/insurance
        if code in BANK_CODES or code in INSURANCE_BROKER or code in BORING:
            excluded.add(code)
            reasons[code] = "sector_exclude"
            continue

        # 3. ST detection (max daily change < 5.5% in last 60 days)
        n = min(60, len(closes))
        max_change = 0.0
        for i in range(len(closes) - n + 1, len(closes)):
            if closes[i-1] > 0:
                ch = abs(closes[i] - closes[i-1]) / closes[i-1]
                max_change = max(max_change, ch)
        if max_change < 0.055 and max_change > 0:
            excluded.add(code)
            reasons[code] = "likely_ST"
            continue

        # 4. Remove ultra-low liquidity (avg daily amount < 30M CNY)
        recent_n = min(20, len(closes))
        avg_amount = sum(
            closes[-recent_n+i] * volumes[-recent_n+i] for i in range(recent_n)
        ) / recent_n
        if avg_amount < 30_000_000:
            excluded.add(code)
            reasons[code] = "low_liquidity"
            continue

        # 5. Remove stocks that have been in continuous decline > 40% in 6 months
        six_mo = min(120, len(closes))
        if closes[-six_mo] > 0:
            six_mo_ret = (closes[-1] - closes[-six_mo]) / closes[-six_mo]
            if six_mo_ret < -0.40:
                excluded.add(code)
                reasons[code] = "deep_decline_6m"
                continue

    # Apply exclusions
    filtered = {k: v for k, v in data.items() if k not in excluded}
    print(f"\nAfter exclusions: {len(filtered)}")
    
    # Count exclusion reasons
    from collections import Counter
    reason_counts = Counter(reasons.values())
    for r, c in reason_counts.most_common():
        print(f"  Excluded ({r}): {c}")

    # === QUALITY SCORING ===
    scored = []
    for code, sd in filtered.items():
        closes = sd["close"]
        volumes = sd["volume"]
        n = len(closes)
        
        # Factor 1: Average daily turnover (liquidity)
        recent_20 = min(20, n)
        avg_amount = sum(
            closes[-recent_20+i] * volumes[-recent_20+i] for i in range(recent_20)
        ) / recent_20
        liquidity_score = min(avg_amount / 1e9, 5.0)  # cap at 5B
        
        # Factor 2: Volatility (we WANT stocks that move — more alpha opportunity)
        daily_rets = []
        for i in range(max(1, n-60), n):
            if closes[i-1] > 0:
                daily_rets.append((closes[i] - closes[i-1]) / closes[i-1])
        volatility = statistics.stdev(daily_rets) if len(daily_rets) > 5 else 0
        vol_score = min(volatility * 100, 5.0)  # normalized
        
        # Factor 3: Recent momentum (20d return) — mild preference for trending stocks
        if n >= 20 and closes[-20] > 0:
            ret_20d = (closes[-1] - closes[-20]) / closes[-20]
        else:
            ret_20d = 0
        # We don't want pure momentum chasers, but avoid deep fallers
        momentum_score = max(min(ret_20d * 10, 3.0), -1.0)
        
        # Factor 4: Limit-up count (market attention / retail interest)
        limit_ups = 0
        for i in range(max(1, n-60), n):
            if closes[i-1] > 0:
                dr = (closes[i] - closes[i-1]) / closes[i-1]
                if dr >= 0.095:
                    limit_ups += 1
        attention_score = min(limit_ups * 0.5, 3.0)
        
        # Factor 5: Price range bonus (sweet spot 10-200 CNY — retail-friendly)
        price = closes[-1]
        if 10 <= price <= 200:
            price_score = 1.0
        elif 5 <= price < 10 or 200 < price <= 500:
            price_score = 0.5
        else:
            price_score = 0.0
        
        # Board bonus (slightly prefer ChiNext/STAR for higher volatility)
        board_bonus = 0.0
        if code.startswith("sz_30") or code.startswith("sh_68"):
            board_bonus = 0.5  # 创业板/科创板
        
        total = liquidity_score + vol_score + momentum_score + attention_score + price_score + board_bonus
        
        scored.append({
            "code": code,
            "total": total,
            "price": round(price, 2),
            "liquidity": round(liquidity_score, 2),
            "volatility": round(vol_score, 2),
            "momentum": round(momentum_score, 2),
            "attention": round(attention_score, 2),
            "ret_20d": round(ret_20d * 100, 1) if ret_20d else 0,
        })

    # Sort by total score
    scored.sort(key=lambda x: x["total"], reverse=True)

    # Take top 300-500
    for target in [300, 500, 800, 1000]:
        print(f"\nTop {target} cutoff score: {scored[min(target-1, len(scored)-1)]['total']:.2f}")

    # Let's go with 500
    TOP_N = 500
    selected = scored[:TOP_N]
    
    print(f"\n=== Selected {TOP_N} stocks ===")
    
    # Board distribution
    sh_main = sum(1 for s in selected if s["code"].startswith("sh_60"))
    sh_star = sum(1 for s in selected if s["code"].startswith("sh_68"))
    sz_main = sum(1 for s in selected if s["code"].startswith("sz_00"))
    sz_gem = sum(1 for s in selected if s["code"].startswith("sz_30"))
    print(f"  SH Main: {sh_main} | STAR: {sh_star} | SZ Main: {sz_main} | ChiNext: {sz_gem}")
    
    prices = [s["price"] for s in selected]
    print(f"  Price: min={min(prices):.0f} median={statistics.median(prices):.0f} max={max(prices):.0f}")
    
    # Show top 20
    print(f"\n{'Rank':<5} {'Code':<15} {'Score':<8} {'Price':<10} {'Liq':<6} {'Vol':<6} {'Mom':<6} {'Att':<6} {'20dRet'}")
    print("=" * 85)
    for i, s in enumerate(selected[:20]):
        print(f"{i+1:<5} {s['code']:<15} {s['total']:<8.2f} {s['price']:<10} {s['liquidity']:<6} {s['volatility']:<6} {s['momentum']:<6} {s['attention']:<6} {s['ret_20d']:+.1f}%")

    # Save the curated pool
    pool_codes = [s["code"] for s in selected]
    output = {
        "version": "v2",
        "description": "Curated A-share pool: no ST/banks/penny/low-liq/deep-decline, sorted by quality",
        "count": len(pool_codes),
        "criteria": {
            "min_price": 5.0,
            "min_daily_amount": "30M CNY",
            "min_data_days": 120,
            "exclude": "ST, banks, insurance, brokers, utilities, 6m decline > 40%",
            "sort_by": "liquidity + volatility + momentum + market_attention + price_range + board_bonus"
        },
        "codes": pool_codes,
        "scored": selected,
    }
    
    with open("data/curated_pool_v2.json", "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to data/curated_pool_v2.json")

    # Also save just the code list for easy loading
    with open("data/curated_pool_codes.txt", "w") as f:
        f.write("\n".join(pool_codes))
    print(f"Saved code list to data/curated_pool_codes.txt")


if __name__ == "__main__":
    main()
