"""
A-Share (China Stock) Scanner for FinClaw
==========================================
Scans major A-share stocks and recommends buys based on technical indicators.
Uses yfinance with .SS (Shanghai) and .SZ (Shenzhen) suffixes.
"""

from __future__ import annotations

import sys
import numpy as np
from typing import Optional

from src.ta import rsi, macd, bollinger_bands


# ── Stock Universe ───────────────────────────────────────────────────

TOP50 = [
    ('600519.SS', '贵州茅台', 'consumer'),
    ('300750.SZ', '宁德时代', 'manufacturing'),
    ('002594.SZ', '比亚迪', 'manufacturing'),
    ('600036.SS', '招商银行', 'bank'),
    ('601318.SS', '中国平安', 'bank'),
    ('000858.SZ', '五粮液', 'consumer'),
    ('601899.SS', '紫金矿业', 'energy'),
    ('600900.SS', '长江电力', 'energy'),
    ('000333.SZ', '美的集团', 'manufacturing'),
    ('300059.SZ', '东方财富', 'tech'),
    ('002230.SZ', '科大讯飞', 'tech'),
    ('002415.SZ', '海康威视', 'tech'),
    ('600276.SS', '恒瑞医药', 'pharma'),
    ('300760.SZ', '迈瑞医疗', 'pharma'),
    ('601012.SS', '隆基绿能', 'energy'),
    ('600031.SS', '三一重工', 'manufacturing'),
    ('601888.SS', '中国中免', 'consumer'),
    ('000725.SZ', '京东方A', 'tech'),
    ('002475.SZ', '立讯精密', 'tech'),
    ('688981.SS', '中芯国际', 'tech'),
    ('002714.SZ', '牧原股份', 'consumer'),
    ('601633.SS', '长城汽车', 'manufacturing'),
    ('600809.SS', '山西汾酒', 'consumer'),
    ('002352.SZ', '顺丰控股', 'manufacturing'),
    ('600030.SS', '中信证券', 'bank'),
    ('601668.SS', '中国建筑', 'manufacturing'),
    ('601398.SS', '工商银行', 'bank'),
    ('601288.SS', '农业银行', 'bank'),
    ('000002.SZ', '万科A', 'manufacturing'),
    ('603288.SS', '海天味业', 'consumer'),
    ('600887.SS', '伊利股份', 'consumer'),
    ('000651.SZ', '格力电器', 'manufacturing'),
    ('601166.SS', '兴业银行', 'bank'),
    ('600585.SS', '海螺水泥', 'manufacturing'),
    ('601857.SS', '中国石油', 'energy'),
    ('600050.SS', '中国联通', 'tech'),
    ('000568.SZ', '泸州老窖', 'consumer'),
    ('601088.SS', '中国神华', 'energy'),
    ('600309.SS', '万华化学', 'manufacturing'),
    ('002304.SZ', '洋河股份', 'consumer'),
]

SECTORS: dict[str, list[tuple[str, str, str]]] = {}
for _ticker, _name, _sector in TOP50:
    SECTORS.setdefault(_sector, []).append((_ticker, _name, _sector))

VALID_SECTORS = sorted(SECTORS.keys())


# ── Scoring Engine ───────────────────────────────────────────────────

def compute_score(
    close: np.ndarray,
    volume: np.ndarray | None = None,
) -> dict:
    """Compute technical score for a price series.

    Returns dict with keys:
        score, rsi_val, macd_hist, pct_b, change_1d, change_5d, volume_ratio,
        signal, price, reasons
    """
    close = np.asarray(close, dtype=np.float64)
    if len(close) < 30:
        return _empty_result(close)

    price = float(close[-1])
    score = 0
    reasons: list[str] = []

    # RSI
    rsi_arr = rsi(close, 14)
    rsi_val = float(rsi_arr[-1]) if not np.isnan(rsi_arr[-1]) else 50.0

    if rsi_val < 30:
        score += 4
        reasons.append(f"RSI oversold({rsi_val:.0f})")
    elif rsi_val < 40:
        score += 3
        reasons.append(f"RSI oversold({rsi_val:.0f})")
    elif rsi_val < 50:
        score += 1
    elif rsi_val > 70:
        score -= 2
        reasons.append(f"RSI overbought({rsi_val:.0f})")

    # MACD histogram
    _macd_line, _macd_signal, macd_hist_arr = macd(close)
    macd_hist_val = float(macd_hist_arr[-1]) if not np.isnan(macd_hist_arr[-1]) else 0.0

    if macd_hist_val > 0:
        score += 2
        reasons.append("MACD golden cross")

    # Bollinger %B
    bb = bollinger_bands(close)
    pct_b_arr = bb['pct_b']
    pct_b_val = float(pct_b_arr[-1]) * 100 if not np.isnan(pct_b_arr[-1]) else 50.0

    if pct_b_val < 20:
        score += 3
        reasons.append("near Bollinger lower")
    elif pct_b_val < 40:
        score += 1

    # 5-day price change
    if len(close) >= 6:
        change_5d = (close[-1] / close[-6] - 1) * 100
    else:
        change_5d = 0.0

    if 0 < change_5d <= 8:
        score += 2

    # 1-day price change
    if len(close) >= 2:
        change_1d = (close[-1] / close[-2] - 1) * 100
    else:
        change_1d = 0.0

    # Volume ratio
    volume_ratio = 0.0
    if volume is not None and len(volume) >= 21:
        vol = np.asarray(volume, dtype=np.float64)
        avg_vol = np.mean(vol[-21:-1])
        if avg_vol > 0:
            volume_ratio = float(vol[-1] / avg_vol)
            if 1.2 <= volume_ratio <= 3.0:
                score += 1
                reasons.append(f"volume up {volume_ratio:.1f}x")

    signal = classify_signal(score)

    return {
        "score": score,
        "rsi_val": rsi_val,
        "macd_hist": macd_hist_val,
        "pct_b": pct_b_val,
        "change_1d": change_1d,
        "change_5d": change_5d,
        "volume_ratio": volume_ratio,
        "signal": signal,
        "price": price,
        "reasons": reasons,
    }


def classify_signal(score: int) -> str:
    """Classify score into signal string."""
    if score >= 6:
        return "** BUY"
    elif score >= 4:
        return "WATCH"
    else:
        return "HOLD"


def _empty_result(close: np.ndarray) -> dict:
    price = float(close[-1]) if len(close) > 0 else 0.0
    return {
        "score": 0,
        "rsi_val": 50.0,
        "macd_hist": 0.0,
        "pct_b": 50.0,
        "change_1d": 0.0,
        "change_5d": 0.0,
        "volume_ratio": 0.0,
        "signal": "HOLD",
        "price": price,
        "reasons": [],
    }


# ── Stock Selection ──────────────────────────────────────────────────

def get_stock_universe(
    top: int = 30,
    sector: str | None = None,
) -> list[tuple[str, str, str]]:
    """Return list of (ticker, name, sector) based on filters."""
    if sector:
        sector_lower = sector.lower()
        if sector_lower not in SECTORS:
            raise ValueError(
                f"Unknown sector '{sector}'. Valid: {', '.join(VALID_SECTORS)}"
            )
        return SECTORS[sector_lower]
    return TOP50[:top]


# ── Scanner ──────────────────────────────────────────────────────────

def scan_cn_stocks(
    top: int = 30,
    sector: str | None = None,
    min_score: int = 0,
    sort_by: str = "score",
) -> list[dict]:
    """Scan A-share stocks and return scored results.

    Returns list of dicts with keys: ticker, name, sector, code, + score fields.
    """
    from src.data.cache import DataCache
    import logging
    import warnings

    universe = get_stock_universe(top=top, sector=sector)
    cache = DataCache()
    results: list[dict] = []

    for ticker, name, sect in universe:
        # Fetch data via yfinance
        cache_key = f"cn_{ticker}_3mo"
        df = cache.get(cache_key, max_age_hours=12)

        if df is None:
            try:
                import yfinance as yf
                logging.getLogger("yfinance").setLevel(logging.CRITICAL)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    stock = yf.Ticker(ticker)
                    df = stock.history(period="3mo")
                if df is not None and not df.empty:
                    cache.set(cache_key, df)
            except Exception as e:
                print(f"  ERROR fetching {ticker}: {e}")
                continue

        if df is None or len(df) < 30:
            continue

        close = np.array(df["Close"].tolist(), dtype=np.float64)
        volume = np.array(df["Volume"].tolist(), dtype=np.float64) if "Volume" in df.columns else None

        result = compute_score(close, volume)
        # Extract code from ticker (e.g. "600519" from "600519.SS")
        code = ticker.split(".")[0]
        result.update({
            "ticker": ticker,
            "name": name,
            "sector": sect,
            "code": code,
        })
        results.append(result)

    # Filter by min_score
    if min_score > 0:
        results = [r for r in results if r["score"] >= min_score]

    # Sort
    sort_key = sort_by.lower()
    if sort_key == "rsi":
        results.sort(key=lambda r: r["rsi_val"])
    elif sort_key == "price":
        results.sort(key=lambda r: r["price"], reverse=True)
    elif sort_key == "change":
        results.sort(key=lambda r: r["change_1d"], reverse=True)
    else:  # default: score descending
        results.sort(key=lambda r: r["score"], reverse=True)

    return results


# ── Output Formatting ────────────────────────────────────────────────

def format_scan_output(results: list[dict], version: str = "5.1.0") -> str:
    """Format scan results as a table string (ASCII-safe)."""
    lines: list[str] = []
    lines.append("")
    lines.append(f"  A-Share Scanner -- FinClaw v{version}")
    lines.append("  " + "=" * 90)
    # Header
    header = (
        f"  {'Rank':<5} {'Name':<14} {'Code':<10} {'Price':>8} "
        f"{'RSI':>6} {'MACD':>7} {'%B':>6} {'1D%':>6} {'5D%':>6} "
        f"{'VR':>5} {'Score':>6} {'Signal'}"
    )
    lines.append(header)
    lines.append("  " + "-" * 90)

    for i, r in enumerate(results, 1):
        name_display = r["name"]
        # Truncate name to 12 chars for alignment
        if len(name_display) > 12:
            name_display = name_display[:12]

        line = (
            f"  {i:<5} {name_display:<14} {r['code']:<10} {r['price']:>8.2f} "
            f"{r['rsi_val']:>6.1f} {r['macd_hist']:>+7.2f} {r['pct_b']:>5.1f} "
            f"{r['change_1d']:>+5.1f} {r['change_5d']:>+5.1f} "
            f"{r['volume_ratio']:>5.1f} {r['score']:>5} {r['signal']}"
        )
        lines.append(line)

    # Recommendations
    recommended = [r for r in results if r["score"] >= 5]
    if recommended:
        lines.append("")
        lines.append("  Recommended (Score >= 5):")
        for r in recommended:
            reason_str = ", ".join(r["reasons"]) if r["reasons"] else "composite"
            lines.append(
                f"    {r['name']} ({r['code']}) Score={r['score']} -- {reason_str}"
            )

    lines.append("")
    return "\n".join(lines)
