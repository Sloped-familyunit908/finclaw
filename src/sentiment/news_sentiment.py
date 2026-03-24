"""
News Sentiment Analyzer (LLM-free)
===================================
Fetches news from free APIs and performs keyword-based sentiment analysis.
Caches results daily to data/sentiment/ directory.

Supported sources:
  - CryptoCompare News API (free, no key needed)
  - AKShare stock_news_em() for A-share news

No external LLM dependency — uses keyword matching only.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError

# ---------------------------------------------------------------------------
# Keyword dictionaries
# ---------------------------------------------------------------------------

POSITIVE_WORDS_EN = {
    # strong bullish
    "surge", "surges", "surging", "rally", "rallies", "rallying",
    "bullish", "breakthrough", "breakout", "soar", "soars", "soaring",
    "moon", "mooning", "pump", "pumping",
    # moderate bullish
    "gain", "gains", "rise", "rises", "rising", "climb", "climbs",
    "up", "upside", "higher", "high", "record", "recovery", "recover",
    "boost", "boosted", "growth", "buy", "buying", "accumulate",
    "outperform", "inflow", "adoption", "approval", "upgrade",
    "partnership", "milestone", "launch", "institutional",
}

NEGATIVE_WORDS_EN = {
    # strong bearish
    "crash", "crashes", "crashing", "dump", "dumps", "dumping",
    "bearish", "plunge", "plunges", "plunging", "collapse", "collapsed",
    # moderate bearish
    "fear", "panic", "sell", "selling", "selloff", "decline", "declining",
    "drop", "drops", "dropping", "fall", "falls", "falling",
    "loss", "losses", "lower", "low", "downside", "down",
    "hack", "hacked", "exploit", "scam", "fraud", "ban", "banned",
    "lawsuit", "investigation", "warning", "risk", "outflow",
    "vulnerability", "attack",
}

POSITIVE_WORDS_ZH = {
    "涨", "上涨", "大涨", "涨停", "暴涨", "突破", "利好",
    "创新高", "新高", "反弹", "回升", "走强", "强势",
    "增长", "盈利", "牛市", "买入", "看好", "利多",
}

NEGATIVE_WORDS_ZH = {
    "跌", "下跌", "大跌", "跌停", "暴跌", "利空",
    "恐慌", "崩盘", "破位", "走弱", "弱势", "下行",
    "亏损", "熊市", "卖出", "看空", "利淡",
    "爆仓", "清算", "风险",
}

# ---------------------------------------------------------------------------
# Sentiment scoring
# ---------------------------------------------------------------------------


def score_text(text: str) -> float:
    """
    Score a piece of text for sentiment using keyword matching.

    Returns a value in [-1, 1]:
      -1 = very negative
       0 = neutral
      +1 = very positive
    """
    text_lower = text.lower()
    words_en = set(re.findall(r"[a-z]+", text_lower))

    pos_en = len(words_en & POSITIVE_WORDS_EN)
    neg_en = len(words_en & NEGATIVE_WORDS_EN)

    # Chinese keyword matching (character-level substring)
    pos_zh = sum(1 for w in POSITIVE_WORDS_ZH if w in text)
    neg_zh = sum(1 for w in NEGATIVE_WORDS_ZH if w in text)

    pos_total = pos_en + pos_zh
    neg_total = neg_en + neg_zh
    total = pos_total + neg_total

    if total == 0:
        return 0.0

    return (pos_total - neg_total) / total


def normalize_score(raw: float) -> float:
    """Convert [-1, 1] raw score to [0, 1] factor score."""
    return max(0.0, min(1.0, 0.5 + raw * 0.5))


# ---------------------------------------------------------------------------
# News fetching
# ---------------------------------------------------------------------------

_HEADERS = {
    "User-Agent": "FinClaw/5.5 (sentiment; +https://github.com/finclaw)"
}


def fetch_crypto_news(timeout: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch latest crypto news from CryptoCompare (free, no key).

    Returns list of dicts with keys: title, source, published_ts
    """
    url = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
    try:
        req = Request(url, headers=_HEADERS)
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        articles = []
        for item in data.get("Data", []):
            articles.append({
                "title": item.get("title", ""),
                "source": item.get("source", ""),
                "published_ts": item.get("published_on", 0),
                "categories": item.get("categories", ""),
            })
        return articles
    except (URLError, OSError, json.JSONDecodeError, TimeoutError):
        return []


def fetch_cn_stock_news() -> List[Dict[str, Any]]:
    """
    Fetch A-share news via AKShare (if installed).

    Returns list of dicts with keys: title, source, published_ts
    """
    try:
        import akshare as ak  # type: ignore
        df = ak.stock_news_em()
        articles = []
        for _, row in df.iterrows():
            title = str(row.get("新闻标题", row.get("title", "")))
            source = str(row.get("新闻来源", row.get("source", "eastmoney")))
            articles.append({
                "title": title,
                "source": source,
                "published_ts": 0,
                "categories": "",
            })
        return articles
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------


def _get_cache_dir() -> Path:
    """Return the cache directory for sentiment data."""
    # Locate project root by walking up from this file
    here = Path(__file__).resolve().parent
    project_root = here.parent.parent  # src/sentiment -> src -> project_root
    cache_dir = project_root / "data" / "sentiment"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _cache_path(date_str: str) -> Path:
    """Return the cache file path for a given date."""
    return _get_cache_dir() / f"sentiment_{date_str}.json"


def save_sentiment_cache(scores: Dict[str, float], date_str: Optional[str] = None) -> Path:
    """
    Save sentiment scores to cache.

    Args:
        scores: Dict mapping symbol/category -> score (0-1)
        date_str: Date string (YYYY-MM-DD), defaults to today UTC

    Returns:
        Path to the saved cache file
    """
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    cache_file = _cache_path(date_str)
    cache_data = {
        "date": date_str,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "scores": scores,
    }
    cache_file.write_text(json.dumps(cache_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return cache_file


def load_sentiment_cache(date_str: Optional[str] = None) -> Optional[Dict[str, float]]:
    """
    Load sentiment scores from cache.

    Args:
        date_str: Date string (YYYY-MM-DD), defaults to today UTC

    Returns:
        Dict mapping symbol/category -> score (0-1), or None if no cache
    """
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    cache_file = _cache_path(date_str)
    if not cache_file.exists():
        return None

    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        return data.get("scores", {})
    except (json.JSONDecodeError, OSError):
        return None


def load_sentiment_history(days: int = 7) -> List[Dict[str, Any]]:
    """
    Load sentiment scores for the last N days.

    Returns list of dicts with 'date' and 'scores' keys, ordered oldest first.
    """
    from datetime import timedelta

    results = []
    today = datetime.now(timezone.utc)
    for i in range(days - 1, -1, -1):
        date = today - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        scores = load_sentiment_cache(date_str)
        if scores is not None:
            results.append({"date": date_str, "scores": scores})
    return results


# ---------------------------------------------------------------------------
# Main analysis pipeline
# ---------------------------------------------------------------------------


def analyze_news_sentiment(
    include_crypto: bool = True,
    include_cn: bool = False,
    save_cache: bool = True,
) -> Dict[str, float]:
    """
    Fetch news and compute sentiment scores.

    Args:
        include_crypto: Include CryptoCompare news
        include_cn: Include A-share news (requires akshare)
        save_cache: Whether to save results to cache

    Returns:
        Dict mapping category -> score (0-1 normalized)
    """
    all_articles: List[Dict[str, Any]] = []

    if include_crypto:
        all_articles.extend(fetch_crypto_news())

    if include_cn:
        all_articles.extend(fetch_cn_stock_news())

    if not all_articles:
        scores = {"overall": 0.5}
        if save_cache:
            save_sentiment_cache(scores)
        return scores

    # Score each article
    raw_scores = [score_text(a["title"]) for a in all_articles]
    overall_raw = sum(raw_scores) / len(raw_scores) if raw_scores else 0.0

    scores = {
        "overall": normalize_score(overall_raw),
        "article_count": len(all_articles),
    }

    # Per-source breakdown
    source_scores: Dict[str, List[float]] = {}
    for article, raw in zip(all_articles, raw_scores):
        src = article.get("source", "unknown")
        source_scores.setdefault(src, []).append(raw)

    for src, src_raw in source_scores.items():
        avg = sum(src_raw) / len(src_raw)
        scores[f"source_{src}"] = normalize_score(avg)

    if save_cache:
        save_sentiment_cache(scores)

    return scores


def get_current_sentiment(symbol: str = "overall") -> float:
    """
    Get the current sentiment score for a symbol/category.
    Falls back to 0.5 (neutral) if no cached data.

    Args:
        symbol: Symbol or category key (default "overall")

    Returns:
        Score in [0, 1]
    """
    cached = load_sentiment_cache()
    if cached is None:
        return 0.5
    return cached.get(symbol, cached.get("overall", 0.5))


def get_sentiment_momentum(symbol: str = "overall", days: int = 7) -> float:
    """
    Compute sentiment momentum — is sentiment improving or worsening?

    Returns a value in [0, 1]:
      < 0.5 means sentiment is getting worse
      = 0.5 means stable
      > 0.5 means sentiment is improving

    Args:
        symbol: Symbol or category key
        days: Number of days to look back

    Returns:
        Momentum score in [0, 1]
    """
    history = load_sentiment_history(days)

    if len(history) < 2:
        return 0.5  # Not enough data

    # Extract scores for the symbol
    values = []
    for entry in history:
        s = entry["scores"].get(symbol, entry["scores"].get("overall", 0.5))
        # Handle non-float values (e.g. article_count)
        if isinstance(s, (int, float)):
            values.append(float(s))
        else:
            values.append(0.5)

    if len(values) < 2:
        return 0.5

    # Weighted average of recent changes (more recent = higher weight)
    changes = []
    weights = []
    for i in range(1, len(values)):
        change = values[i] - values[i - 1]
        changes.append(change)
        weights.append(i)  # More recent changes get higher weight

    total_weight = sum(weights)
    if total_weight == 0:
        return 0.5

    weighted_change = sum(c * w for c, w in zip(changes, weights)) / total_weight

    # Normalize: typical daily sentiment change is ±0.1
    # Map [-0.2, +0.2] -> [0, 1]
    momentum = 0.5 + weighted_change * 2.5
    return max(0.0, min(1.0, momentum))
