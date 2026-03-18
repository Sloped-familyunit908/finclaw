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

from src.ta import rsi, macd, bollinger_bands, sma


# ── Stock Universe ───────────────────────────────────────────────────

# Legacy alias – kept for backward compatibility
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

# ── Expanded Universe (~160 stocks) ──────────────────────────────────

CN_UNIVERSE: list[tuple[str, str, str]] = [
    # ── bank / 金融 ──
    ('600036.SS', '招商银行', 'bank'),
    ('601318.SS', '中国平安', 'bank'),
    ('600030.SS', '中信证券', 'bank'),
    ('601398.SS', '工商银行', 'bank'),
    ('601288.SS', '农业银行', 'bank'),
    ('601166.SS', '兴业银行', 'bank'),
    ('601939.SS', '建设银行', 'bank'),
    ('600000.SS', '浦发银行', 'bank'),
    ('601328.SS', '交通银行', 'bank'),
    ('600016.SS', '民生银行', 'bank'),
    # ── tech ──
    ('300059.SZ', '东方财富', 'tech'),
    ('002415.SZ', '海康威视', 'tech'),
    ('000725.SZ', '京东方A', 'tech'),
    ('002475.SZ', '立讯精密', 'tech'),
    ('688981.SS', '中芯国际', 'tech'),
    ('600050.SS', '中国联通', 'tech'),
    ('002236.SZ', '大华股份', 'tech'),
    ('300496.SZ', '中科创达', 'tech'),
    # ── consumer / 大消费 ──
    ('600519.SS', '贵州茅台', 'consumer'),
    ('000858.SZ', '五粮液', 'consumer'),
    ('601888.SS', '中国中免', 'consumer'),
    ('002714.SZ', '牧原股份', 'consumer'),
    ('600809.SS', '山西汾酒', 'consumer'),
    ('603288.SS', '海天味业', 'consumer'),
    ('600887.SS', '伊利股份', 'consumer'),
    ('000568.SZ', '泸州老窖', 'consumer'),
    ('002304.SZ', '洋河股份', 'consumer'),
    ('600600.SS', '青岛啤酒', 'consumer'),
    ('000895.SZ', '双汇发展', 'consumer'),
    # ── energy / 能源 ──
    ('601899.SS', '紫金矿业', 'energy'),
    ('600900.SS', '长江电力', 'energy'),
    ('601857.SS', '中国石油', 'energy'),
    ('601088.SS', '中国神华', 'energy'),
    ('600028.SS', '中国石化', 'energy'),
    ('601225.SS', '陕西煤业', 'energy'),
    ('600188.SS', '兖矿能源', 'energy'),
    # ── pharma / 医药 ──
    ('600276.SS', '恒瑞医药', 'pharma'),
    ('300760.SZ', '迈瑞医疗', 'pharma'),
    ('000538.SZ', '云南白药', 'pharma'),
    ('600196.SS', '复星医药', 'pharma'),
    ('300122.SZ', '智飞生物', 'pharma'),
    ('300015.SZ', '爱尔眼科', 'pharma'),
    ('002007.SZ', '华兰生物', 'pharma'),
    # ── manufacturing / 制造 ──
    ('300750.SZ', '宁德时代', 'manufacturing'),
    ('000333.SZ', '美的集团', 'manufacturing'),
    ('600031.SS', '三一重工', 'manufacturing'),
    ('601633.SS', '长城汽车', 'manufacturing'),
    ('002352.SZ', '顺丰控股', 'manufacturing'),
    ('601668.SS', '中国建筑', 'manufacturing'),
    ('000651.SZ', '格力电器', 'manufacturing'),
    ('600585.SS', '海螺水泥', 'manufacturing'),
    ('600309.SS', '万华化学', 'manufacturing'),
    ('601766.SS', '中国中车', 'manufacturing'),
    ('002008.SZ', '大族激光', 'manufacturing'),
    ('601100.SS', '恒立液压', 'manufacturing'),
    # ── ai / AI概念 ──
    ('002230.SZ', '科大讯飞', 'ai'),
    ('688041.SS', '海光信息', 'ai'),
    ('688256.SS', '寒武纪', 'ai'),
    ('603019.SS', '中科曙光', 'ai'),
    ('000977.SZ', '浪潮信息', 'ai'),
    ('300229.SZ', '拓尔思', 'ai'),
    ('688111.SS', '金山办公', 'ai'),
    ('300418.SZ', '昆仑万维', 'ai'),
    ('601360.SS', '三六零', 'ai'),
    # ── optical / 光模块 ──
    ('300308.SZ', '中际旭创', 'optical'),
    ('300394.SZ', '天孚通信', 'optical'),
    ('300502.SZ', '新易盛', 'optical'),
    ('002281.SZ', '光迅科技', 'optical'),
    ('300570.SZ', '太辰光', 'optical'),
    ('688498.SS', '源杰科技', 'optical'),
    ('000988.SZ', '华工科技', 'optical'),
    ('603083.SS', '剑桥科技', 'optical'),
    # ── storage / 存储/半导体存储 ──
    ('603986.SS', '兆易创新', 'storage'),
    ('300223.SZ', '北京君正', 'storage'),
    ('688008.SS', '澜起科技', 'storage'),
    ('688002.SS', '睿创微纳', 'storage'),
    ('688525.SS', '佰维存储', 'storage'),
    ('301308.SZ', '江波龙', 'storage'),
    ('300042.SZ', '朗科科技', 'storage'),
    ('000021.SZ', '深科技', 'storage'),
    # ── chip / 芯片 ──
    ('603501.SS', '韦尔股份', 'chip'),
    ('002371.SZ', '北方华创', 'chip'),
    ('688012.SS', '中微公司', 'chip'),
    ('300782.SZ', '卓胜微', 'chip'),
    ('300661.SZ', '圣邦股份', 'chip'),
    ('600584.SS', '长电科技', 'chip'),
    ('688347.SS', '华虹公司', 'chip'),
    ('688099.SS', '晶晨股份', 'chip'),
    ('603160.SS', '汇顶科技', 'chip'),
    # ── ev / 新能源车 ──
    ('002594.SZ', '比亚迪', 'ev'),
    ('000625.SZ', '长安汽车', 'ev'),
    ('601127.SS', '赛力斯', 'ev'),
    ('600104.SS', '上汽集团', 'ev'),
    ('601238.SS', '广汽集团', 'ev'),
    ('600733.SS', '北汽蓝谷', 'ev'),
    # ── solar / 光伏 ──
    ('601012.SS', '隆基绿能', 'solar'),
    ('600438.SS', '通威股份', 'solar'),
    ('300274.SZ', '阳光电源', 'solar'),
    ('002129.SZ', 'TCL中环', 'solar'),
    ('002459.SZ', '晶澳科技', 'solar'),
    ('688599.SS', '天合光能', 'solar'),
    # ── military / 军工 ──
    ('600760.SS', '中航沈飞', 'military'),
    ('600893.SS', '航发动力', 'military'),
    ('002179.SZ', '中航光电', 'military'),
    ('002049.SZ', '紫光国微', 'military'),
    ('600372.SS', '中航电子', 'military'),
    ('600150.SS', '中国船舶', 'military'),
    ('601989.SS', '中国重工', 'military'),
    ('000768.SZ', '中航西飞', 'military'),
    # ── liquor / 白酒 ──
    ('600702.SS', '舍得酒业', 'liquor'),
    ('000799.SZ', '酒鬼酒', 'liquor'),
    ('000596.SZ', '古井贡酒', 'liquor'),
    ('600779.SS', '水井坊', 'liquor'),
    ('002646.SZ', '青青稞酒', 'liquor'),
    # ── real_estate / 地产 ──
    ('000002.SZ', '万科A', 'real_estate'),
    ('600048.SS', '保利发展', 'real_estate'),
    ('001979.SZ', '招商蛇口', 'real_estate'),
    ('600383.SS', '金地集团', 'real_estate'),
    ('601155.SS', '新城控股', 'real_estate'),
    # ── telecom / 通信 ──
    ('600941.SS', '中国移动', 'telecom'),
    ('601728.SS', '中国电信', 'telecom'),
    ('000063.SZ', '中兴通讯', 'telecom'),
    ('300628.SZ', '亿联网络', 'telecom'),
    ('002396.SZ', '星网锐捷', 'telecom'),
    ('300590.SZ', '移为通信', 'telecom'),
    ('002194.SZ', '武汉凡谷', 'telecom'),
    # ── additional ai ──
    ('688327.SS', '云从科技', 'ai'),
    ('300459.SZ', '汤姆猫', 'ai'),
    ('688618.SS', '三旺通信', 'ai'),
    # ── additional chip ──
    ('688536.SS', '思瑞浦', 'chip'),
    ('300327.SZ', '中颖电子', 'chip'),
    ('688521.SS', '芯原股份', 'chip'),
    ('688120.SS', '华海清科', 'chip'),
    # ── additional pharma ──
    ('300529.SZ', '健帆生物', 'pharma'),
    ('688185.SS', '康希诺', 'pharma'),
    # ── additional manufacturing ──
    ('002466.SZ', '天齐锂业', 'manufacturing'),
    ('002460.SZ', '赣锋锂业', 'manufacturing'),
    ('300124.SZ', '汇川技术', 'manufacturing'),
    # ── additional consumer ──
    ('603369.SS', '今世缘', 'consumer'),
    ('000568.SZ', '泸州老窖', 'consumer'),
    ('002557.SZ', '洽洽食品', 'consumer'),
    # ── additional energy ──
    ('600011.SS', '华能国际', 'energy'),
    ('600886.SS', '国投电力', 'energy'),
    # ── additional bank ──
    ('600015.SS', '华夏银行', 'bank'),
    ('601818.SS', '光大银行', 'bank'),
    # ── additional ev ──
    ('002074.SZ', '国轩高科', 'ev'),
    ('300014.SZ', '亿纬锂能', 'ev'),
    # ── additional storage ──
    ('688396.SS', '华润微', 'storage'),
    ('603501.SS', '韦尔股份', 'storage'),
    # ── additional optical ──
    ('300602.SZ', '飞荣达', 'optical'),
    # ── additional solar ──
    ('300763.SZ', '锦浪科技', 'solar'),
    ('688223.SS', '晶科能源', 'solar'),
]

# De-duplicate: some tickers appear in both TOP50 (old sectors) and CN_UNIVERSE (new sectors).
# CN_UNIVERSE is the single source of truth.
_seen_tickers: set[str] = set()
_deduped: list[tuple[str, str, str]] = []
for _t, _n, _s in CN_UNIVERSE:
    if _t not in _seen_tickers:
        _seen_tickers.add(_t)
        _deduped.append((_t, _n, _s))
CN_UNIVERSE = _deduped

SECTORS: dict[str, list[tuple[str, str, str]]] = {}
for _ticker, _name, _sector in CN_UNIVERSE:
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


# ── V2 Scoring Engine (multi-signal) ────────────────────────────────

def _signal_volume_breakout(
    close: np.ndarray,
    volume: np.ndarray | None,
) -> tuple[int, str | None]:
    """Volume Breakout: price up >2% AND volume > 2x 20-day average. (+3)"""
    if volume is None or len(close) < 2 or len(volume) < 21:
        return 0, None
    change = (close[-1] / close[-2] - 1) * 100
    vol = np.asarray(volume, dtype=np.float64)
    avg_vol = np.mean(vol[-21:-1])
    if avg_vol <= 0:
        return 0, None
    vol_ratio = vol[-1] / avg_vol
    if change > 2.0 and vol_ratio > 2.0:
        return 3, f"vol breakout(+{change:.1f}%, vol {vol_ratio:.1f}x)"
    return 0, None


def _signal_bottom_reversal(
    close: np.ndarray,
    rsi_val: float,
) -> tuple[int, str | None]:
    """Bottom Reversal: RSI < 25 AND price > prev close (bouncing). (+4)"""
    if len(close) < 2:
        return 0, None
    if rsi_val < 25.0 and close[-1] > close[-2]:
        return 4, f"bottom reversal(RSI={rsi_val:.0f}, bouncing)"
    return 0, None


def _signal_macd_divergence(
    close: np.ndarray,
    macd_hist_arr: np.ndarray,
) -> tuple[int, str | None]:
    """MACD Bullish Divergence: price made new 10-day low but MACD hist didn't. (+3)"""
    if len(close) < 20 or len(macd_hist_arr) < 20:
        return 0, None
    # Check if current price is at or near 10-day low
    recent_10 = close[-10:]
    if close[-1] > np.nanmin(recent_10) * 1.005:  # within 0.5% of 10-day low
        return 0, None
    # Find previous trough: look at days -20 to -10 for a local low
    prev_window = close[-20:-10]
    if len(prev_window) == 0:
        return 0, None
    prev_low_offset = int(np.argmin(prev_window))  # offset within [-20:-10]
    prev_low_idx = len(close) - 20 + prev_low_offset  # absolute index
    # Compare MACD histogram values: current vs previous trough
    curr_hist = macd_hist_arr[-1]
    prev_hist = macd_hist_arr[prev_low_idx] if prev_low_idx < len(macd_hist_arr) else np.nan
    if np.isnan(curr_hist) or np.isnan(prev_hist):
        return 0, None
    # Divergence: price makes new low, but MACD histogram is higher (less negative)
    if close[-1] <= close[prev_low_idx] and curr_hist > prev_hist:
        return 3, "MACD bullish divergence"
    return 0, None


def _signal_ma_alignment(
    close: np.ndarray,
) -> tuple[int, str | None]:
    """MA Alignment: Close > MA5 > MA10 > MA20 (uptrend confirmation). (+2)"""
    if len(close) < 20:
        return 0, None
    ma5 = np.mean(close[-5:])
    ma10 = np.mean(close[-10:])
    ma20 = np.mean(close[-20:])
    if close[-1] > ma5 > ma10 > ma20:
        return 2, "MA alignment(bullish)"
    return 0, None


def _signal_low_volume_pullback(
    close: np.ndarray,
    volume: np.ndarray | None,
) -> tuple[int, str | None]:
    """Low-Volume Pullback: in uptrend (MA20 up), 3-day pullback with declining volume. (+3)"""
    if volume is None or len(close) < 25 or len(volume) < 25:
        return 0, None
    vol = np.asarray(volume, dtype=np.float64)
    # Check uptrend: MA20 rising
    ma20_now = np.mean(close[-20:])
    ma20_5ago = np.mean(close[-25:-5])
    if ma20_now <= ma20_5ago:
        return 0, None
    # Check 3-day pullback (close declining)
    if not (close[-1] < close[-2] or close[-2] < close[-3] or close[-3] < close[-4]):
        # At least 2 of last 3 days should be down
        down_count = sum(1 for i in range(-3, 0) if close[i] < close[i - 1])
        if down_count < 2:
            return 0, None
    # Check declining volume over last 3 days
    if not (vol[-1] < vol[-2] and vol[-2] < vol[-3]):
        return 0, None
    # Price still above MA20
    if close[-1] < ma20_now:
        return 0, None
    return 3, "low-vol pullback(uptrend)"


def _signal_nday_breakout(
    close: np.ndarray,
    n: int = 20,
) -> tuple[int, str | None]:
    """N-Day Breakout: price at N-day high. (+2)"""
    if len(close) < n:
        return 0, None
    n_day_max = np.max(close[-n:])
    if close[-1] >= n_day_max:
        return 2, f"{n}d high breakout"
    return 0, None


def _signal_short_term_reversal(
    close: np.ndarray,
) -> tuple[int, str | None]:
    """Short-Term Reversal: 5-day return < -5% (mean reversion). (+2)"""
    if len(close) < 6:
        return 0, None
    ret_5d = (close[-1] / close[-6] - 1) * 100
    if ret_5d < -5.0:
        return 2, f"5d reversal({ret_5d:+.1f}%)"
    return 0, None


def _signal_momentum_confirmation(
    close: np.ndarray,
) -> tuple[int, str | None]:
    """Momentum Confirmation: 10-day return > 0 AND 20-day return > 0. (+1)"""
    if len(close) < 21:
        return 0, None
    ret_10d = (close[-1] / close[-11] - 1) * 100
    ret_20d = (close[-1] / close[-21] - 1) * 100
    if ret_10d > 0 and ret_20d > 0:
        return 1, "momentum confirmed"
    return 0, None


def compute_score_v2(
    close: np.ndarray,
    volume: np.ndarray | None = None,
) -> dict:
    """Compute enhanced technical score using multi-signal approach (v2).

    Includes all v1 signals plus:
    - Volume Breakout (+3)
    - Bottom Reversal (+4)
    - MACD Bullish Divergence (+3)
    - MA Alignment (+2)
    - Low-Volume Pullback (+3)
    - N-Day Breakout (+2)
    - Short-Term Reversal (+2)
    - Momentum Confirmation (+1)

    Returns dict with same keys as compute_score(), plus ``strategy`` key.
    """
    close = np.asarray(close, dtype=np.float64)
    if len(close) < 30:
        result = _empty_result(close)
        result["strategy"] = "v2"
        return result

    # ── Start with v1 baseline ───────────────────────────────────
    base = compute_score(close, volume)
    score = base["score"]
    reasons = list(base["reasons"])
    rsi_val = base["rsi_val"]

    # ── V2 signals ───────────────────────────────────────────────
    # MACD histogram array (need it for divergence)
    _macd_line, _macd_signal, macd_hist_arr = macd(close)

    signal_funcs = [
        lambda: _signal_volume_breakout(close, volume),
        lambda: _signal_bottom_reversal(close, rsi_val),
        lambda: _signal_macd_divergence(close, macd_hist_arr),
        lambda: _signal_ma_alignment(close),
        lambda: _signal_low_volume_pullback(close, volume),
        lambda: _signal_nday_breakout(close, 20),
        lambda: _signal_short_term_reversal(close),
        lambda: _signal_momentum_confirmation(close),
    ]

    for fn in signal_funcs:
        pts, reason = fn()
        score += pts
        if reason:
            reasons.append(reason)

    signal = classify_signal_v2(score)

    return {
        "score": score,
        "rsi_val": base["rsi_val"],
        "macd_hist": base["macd_hist"],
        "pct_b": base["pct_b"],
        "change_1d": base["change_1d"],
        "change_5d": base["change_5d"],
        "volume_ratio": base["volume_ratio"],
        "signal": signal,
        "price": base["price"],
        "reasons": reasons,
        "strategy": "v2",
    }


def classify_signal_v2(score: int) -> str:
    """Classify v2 score into signal string (higher thresholds)."""
    if score >= 10:
        return "*** STRONG BUY"
    elif score >= 7:
        return "** BUY"
    elif score >= 4:
        return "WATCH"
    else:
        return "HOLD"


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
    return CN_UNIVERSE[:top]


# ── Scanner ──────────────────────────────────────────────────────────

def scan_cn_stocks(
    top: int = 30,
    sector: str | None = None,
    min_score: int = 0,
    sort_by: str = "score",
    strategy: str = "v2",
) -> list[dict]:
    """Scan A-share stocks and return scored results.

    Parameters
    ----------
    strategy : str
        ``"v1"`` for legacy scoring, ``"v2"`` for multi-signal (default).

    Returns list of dicts with keys: ticker, name, sector, code, + score fields.
    """
    from src.data.cache import DataCache
    import logging
    import warnings

    score_fn = compute_score_v2 if strategy == "v2" else compute_score
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

        result = score_fn(close, volume)
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


# ── Backtest Engine ──────────────────────────────────────────────────

def _compute_score_at(
    close: np.ndarray,
    volume: np.ndarray | None,
    idx: int,
    strategy: str = "v1",
) -> dict:
    """Compute the scoring result using data up to (and including) *idx*.

    This slices ``close[:idx+1]`` and ``volume[:idx+1]`` so the scoring
    algorithm sees only data available on that trading day.

    Parameters
    ----------
    strategy : str
        ``"v1"`` for legacy scoring, ``"v2"`` for multi-signal.
    """
    sliced_close = close[: idx + 1]
    sliced_volume = volume[: idx + 1] if volume is not None else None
    score_fn = compute_score_v2 if strategy == "v2" else compute_score
    return score_fn(sliced_close, sliced_volume)


def backtest_cn_strategy(
    *,
    hold_days: int = 5,
    min_score: int = 6,
    period: str = "6mo",
    lookback_days: int = 30,
    sector: str | None = None,
    top: int | None = None,
    data_override: dict[str, dict] | None = None,
    strategy: str = "v1",
) -> dict:
    """Walk-forward backtest of the A-share scoring strategy.

    Parameters
    ----------
    hold_days : int
        How many trading days to hold each selected batch (1/3/5/10/20).
    min_score : int
        Minimum score for a stock to be selected on a given day.
    period : str
        yfinance period string for fetching historical data (e.g. ``"6mo"``).
    lookback_days : int
        How many recent trading days to evaluate (max 90).
    sector : str | None
        Limit backtest to a specific sector, or ``None`` for all.
    top : int | None
        Limit to top-N stocks if no sector is specified.
    data_override : dict | None
        Pre-loaded data keyed by ticker → ``{"close": np.ndarray, "volume": np.ndarray}``.
        When provided, yfinance is **not** called, making unit-tests fast and deterministic.
    strategy : str
        ``"v1"`` for legacy scoring, ``"v2"`` for multi-signal scoring.

    Returns
    -------
    dict
        Keys: ``batches`` (list[dict]), ``summary`` (dict).
    """
    lookback_days = min(max(lookback_days, 1), 90)
    if hold_days not in (1, 3, 5, 10, 20):
        hold_days = 5

    universe = get_stock_universe(
        top=top if top is not None else len(CN_UNIVERSE),
        sector=sector,
    )

    # ── Fetch data ───────────────────────────────────────────────
    stock_data: dict[str, dict] = {}  # ticker → {close, volume, name, sector}

    if data_override is not None:
        for ticker, name, sect in universe:
            if ticker in data_override:
                d = data_override[ticker]
                stock_data[ticker] = {
                    "close": np.asarray(d["close"], dtype=np.float64),
                    "volume": np.asarray(d["volume"], dtype=np.float64) if d.get("volume") is not None else None,
                    "name": name,
                    "sector": sect,
                }
    else:
        import logging
        import warnings

        for ticker, name, sect in universe:
            try:
                import yfinance as yf
                logging.getLogger("yfinance").setLevel(logging.CRITICAL)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    stock = yf.Ticker(ticker)
                    df = stock.history(period=period)
                if df is None or df.empty or len(df) < 60:
                    continue
                stock_data[ticker] = {
                    "close": np.array(df["Close"].tolist(), dtype=np.float64),
                    "volume": np.array(df["Volume"].tolist(), dtype=np.float64) if "Volume" in df.columns else None,
                    "name": name,
                    "sector": sect,
                }
            except Exception:
                continue

    if not stock_data:
        return {"batches": [], "summary": _empty_summary()}

    # ── Determine evaluation window ─────────────────────────────
    # We need at least 30 bars of history *before* the evaluation start,
    # plus ``lookback_days + hold_days`` bars of forward data.
    min_len = min(len(d["close"]) for d in stock_data.values())
    # Start evaluation at index ``start_idx`` and end at ``end_idx``
    # so we can still compute N-day forward return.
    warmup = 30  # minimum bars for indicators
    start_idx = max(warmup, min_len - lookback_days - hold_days)
    end_idx = min_len - hold_days  # last day where forward return is known

    if start_idx >= end_idx:
        return {"batches": [], "summary": _empty_summary()}

    # ── Walk-forward ─────────────────────────────────────────────
    batches: list[dict] = []
    day = start_idx

    while day < end_idx:
        selected: list[dict] = []
        for ticker, info in stock_data.items():
            close = info["close"]
            volume = info["volume"]
            if day >= len(close) - hold_days:
                continue
            result = _compute_score_at(close, volume, day, strategy=strategy)
            if result["score"] >= min_score:
                # Forward return
                entry_price = close[day]
                exit_price = close[min(day + hold_days, len(close) - 1)]
                fwd_return = (exit_price / entry_price - 1) * 100 if entry_price > 0 else 0.0
                selected.append({
                    "ticker": ticker,
                    "name": info["name"],
                    "sector": info["sector"],
                    "score": result["score"],
                    "entry_price": float(entry_price),
                    "exit_price": float(exit_price),
                    "return_pct": float(fwd_return),
                })

        if selected:
            avg_ret = sum(s["return_pct"] for s in selected) / len(selected)
            best = max(selected, key=lambda s: s["return_pct"])
            worst = min(selected, key=lambda s: s["return_pct"])
            batches.append({
                "day_index": day,
                "num_selected": len(selected),
                "avg_return": avg_ret,
                "best_stock": best["name"],
                "best_ticker": best["ticker"],
                "best_return": best["return_pct"],
                "worst_stock": worst["name"],
                "worst_ticker": worst["ticker"],
                "worst_return": worst["return_pct"],
                "stocks": selected,
            })

        day += hold_days  # jump by hold period to avoid overlapping batches

    # ── Summary ──────────────────────────────────────────────────
    summary = _compute_summary(batches, hold_days, min_score)
    return {"batches": batches, "summary": summary}


def _compute_summary(batches: list[dict], hold_days: int, min_score: int) -> dict:
    """Aggregate backtest batches into a summary."""
    if not batches:
        return _empty_summary()

    returns = [b["avg_return"] for b in batches]
    total_batches = len(batches)
    avg_return = sum(returns) / total_batches
    win_count = sum(1 for r in returns if r > 0)
    win_rate = win_count / total_batches * 100
    best_batch = max(returns)
    worst_batch = min(returns)

    # Rough annualization:  (1 + avg_per_period)^(periods_per_year) - 1
    periods_per_year = 252 / max(hold_days, 1)
    avg_per_period = avg_return / 100.0
    ann_return = ((1 + avg_per_period) ** periods_per_year - 1) * 100

    return {
        "total_batches": total_batches,
        "avg_return": avg_return,
        "win_rate": win_rate,
        "best_batch": best_batch,
        "worst_batch": worst_batch,
        "annualized": ann_return,
        "hold_days": hold_days,
        "min_score": min_score,
    }


def _empty_summary() -> dict:
    return {
        "total_batches": 0,
        "avg_return": 0.0,
        "win_rate": 0.0,
        "best_batch": 0.0,
        "worst_batch": 0.0,
        "annualized": 0.0,
        "hold_days": 0,
        "min_score": 0,
    }


def format_backtest_output(result: dict, version: str = "5.1.0", strategy: str = "v1") -> str:
    """Format backtest result dict into a human-readable table."""
    lines: list[str] = []
    summary = result["summary"]
    batches = result["batches"]

    lines.append("")
    lines.append(f"  A-Share Selection Strategy Backtest -- FinClaw v{version} (strategy={strategy})")
    lines.append(
        f"  Hold: {summary.get('hold_days', '?')} days | "
        f"Min Score: {summary.get('min_score', '?')}"
    )
    lines.append("  " + "=" * 90)

    if not batches:
        lines.append("  No selections were made during the backtest period.")
        lines.append("")
        return "\n".join(lines)

    header = (
        f"  {'Batch':<6} {'Selected':>10} {'Avg Ret':>10} "
        f"{'Best Stock':<14} {'Best Ret':>10} "
        f"{'Worst Stock':<14} {'Worst Ret':>10}"
    )
    lines.append(header)
    lines.append("  " + "-" * 90)

    for i, b in enumerate(batches, 1):
        best_name = b["best_stock"]
        worst_name = b["worst_stock"]
        if len(best_name) > 12:
            best_name = best_name[:12]
        if len(worst_name) > 12:
            worst_name = worst_name[:12]
        line = (
            f"  {i:<6} {b['num_selected']:>8} stk {b['avg_return']:>+9.2f}% "
            f"{best_name:<14} {b['best_return']:>+9.2f}% "
            f"{worst_name:<14} {b['worst_return']:>+9.2f}%"
        )
        lines.append(line)

    lines.append("")
    lines.append("  Summary:")
    lines.append(f"    Total batches:      {summary['total_batches']}")
    lines.append(f"    Avg batch return:   {summary['avg_return']:+.2f}% ({summary.get('hold_days','?')}-day hold)")
    lines.append(f"    Win rate:           {summary['win_rate']:.1f}%")
    lines.append(f"    Best batch:         {summary['best_batch']:+.2f}%")
    lines.append(f"    Worst batch:        {summary['worst_batch']:+.2f}%")
    lines.append(f"    Annualized (est):   {summary['annualized']:+.1f}%")
    lines.append("")
    return "\n".join(lines)
