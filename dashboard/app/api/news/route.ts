/* ════════════════════════════════════════════════════════════════
   API ROUTE — /api/news  — FinClaw
   Fetches financial news for US stocks, A-shares, crypto, or
   general market news.
   - Uses Next.js API route as CORS proxy
   - Caches results for 10 minutes
   - Max 10 results per ticker
   - Never crashes — returns [] on error
   ════════════════════════════════════════════════════════════════ */

import { NextRequest, NextResponse } from "next/server";

export interface NewsItem {
  title: string;
  url: string;
  source: string;
  publishedAt: string;
}

/* ── Simple in-memory cache (10 min) ── */
const cache: Record<string, { data: NewsItem[]; ts: number }> = {};
const CACHE_TTL = 10 * 60 * 1000;

function cached(key: string): NewsItem[] | null {
  const entry = cache[key];
  if (entry && Date.now() - entry.ts < CACHE_TTL) return entry.data;
  return null;
}

const UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";

/* ── Detect market type ── */
function isCN(ticker: string): boolean {
  return /\.(SH|SZ)$/i.test(ticker) || /^\d{6}$/.test(ticker);
}

function isCrypto(ticker: string): boolean {
  return ["BTC", "ETH", "SOL", "DOGE", "XRP", "ADA", "DOT", "AVAX", "MATIC", "LINK"].includes(
    ticker.toUpperCase()
  );
}

function isMarket(ticker: string): boolean {
  return ticker.toLowerCase() === "market";
}

/* ── Parse RSS XML without external dependencies ── */
function parseRSSItems(xml: string): Array<{ title: string; link: string; pubDate: string; source: string }> {
  const items: Array<{ title: string; link: string; pubDate: string; source: string }> = [];
  const itemRegex = /<item>([\s\S]*?)<\/item>/gi;
  let match;

  while ((match = itemRegex.exec(xml)) !== null) {
    const block = match[1];

    const titleMatch = block.match(/<title>(?:<!\[CDATA\[)?([\s\S]*?)(?:\]\]>)?<\/title>/i);
    const linkMatch = block.match(/<link>([\s\S]*?)<\/link>/i);
    const pubDateMatch = block.match(/<pubDate>([\s\S]*?)<\/pubDate>/i);
    const sourceMatch = block.match(/<source[^>]*>([\s\S]*?)<\/source>/i);

    const title = titleMatch?.[1]?.trim() ?? "";
    const link = linkMatch?.[1]?.trim() ?? "";
    const pubDate = pubDateMatch?.[1]?.trim() ?? "";
    const source = sourceMatch?.[1]?.trim() ?? "";

    if (title && link) {
      items.push({ title, link, pubDate, source });
    }
  }

  return items;
}

/* ── Google News RSS (US stocks & general market) ── */
async function fetchGoogleNews(query: string, maxResults: number = 10): Promise<NewsItem[]> {
  try {
    const encodedQuery = encodeURIComponent(query);
    const url = `https://news.google.com/rss/search?q=${encodedQuery}&hl=en-US&gl=US&ceid=US:en`;

    const resp = await fetch(url, {
      headers: { "User-Agent": UA },
      signal: AbortSignal.timeout(8000),
    });

    if (!resp.ok) return [];
    const xml = await resp.text();
    const items = parseRSSItems(xml);

    return items.slice(0, maxResults).map((item) => ({
      title: decodeHTMLEntities(item.title),
      url: item.link,
      source: item.source || extractDomain(item.link),
      publishedAt: item.pubDate ? new Date(item.pubDate).toISOString() : new Date().toISOString(),
    }));
  } catch {
    return [];
  }
}

/* ── Eastmoney news (A-shares) ── */
async function fetchEastmoneyNews(ticker: string, maxResults: number = 10): Promise<NewsItem[]> {
  try {
    // Strip .SH/.SZ suffix for search query
    const stockCode = ticker.replace(/\.(SH|SZ)$/i, "");
    const url = `https://search-api-web.eastmoney.com/search/jsonp?cb=jQuery&param=%7B%22uid%22%3A%22%22%2C%22keyword%22%3A%22${stockCode}%22%2C%22type%22%3A%5B%22cmsArticleWebOld%22%5D%2C%22client%22%3A%22web%22%2C%22clientType%22%3A%22web%22%2C%22clientVersion%22%3A%22curr%22%2C%22param%22%3A%7B%22cmsArticleWebOld%22%3A%7B%22searchScope%22%3A%22default%22%2C%22sort%22%3A%22default%22%2C%22pageIndex%22%3A1%2C%22pageSize%22%3A${maxResults}%2C%22preTag%22%3A%22%22%2C%22postTag%22%3A%22%22%7D%7D%7D`;

    const resp = await fetch(url, {
      headers: {
        "User-Agent": UA,
        Referer: "https://so.eastmoney.com/",
      },
      signal: AbortSignal.timeout(8000),
    });

    if (!resp.ok) {
      // Fallback to Google News for Chinese stocks
      return fetchGoogleNews(`${stockCode} 股票 新闻`, maxResults);
    }

    const text = await resp.text();
    // Parse JSONP: jQuery(...) → extract JSON
    const jsonStr = text.replace(/^jQuery\w*\(/, "").replace(/\);?\s*$/, "");

    if (!jsonStr || jsonStr === text) {
      return fetchGoogleNews(`${stockCode} stock`, maxResults);
    }

    const json = JSON.parse(jsonStr);
    const articles = json?.result?.cmsArticleWebOld ?? [];

    if (!Array.isArray(articles) || articles.length === 0) {
      return fetchGoogleNews(`${stockCode} stock A shares`, maxResults);
    }

    return articles.slice(0, maxResults).map((a: Record<string, string>) => ({
      title: (a.title || "").replace(/<[^>]+>/g, ""),
      url: a.url || a.articleUrl || "",
      source: a.mediaName || "eastmoney.com",
      publishedAt: a.date
        ? new Date(a.date).toISOString()
        : new Date().toISOString(),
    })).filter((item: NewsItem) => item.title && item.url);
  } catch {
    // Fallback to Google News
    const stockCode = ticker.replace(/\.(SH|SZ)$/i, "");
    return fetchGoogleNews(`${stockCode} stock`, maxResults);
  }
}

/* ── Crypto news (CoinTelegraph RSS) ── */
async function fetchCryptoNews(ticker: string, maxResults: number = 10): Promise<NewsItem[]> {
  // Try CoinTelegraph RSS first
  try {
    const resp = await fetch("https://cointelegraph.com/rss", {
      headers: { "User-Agent": UA },
      signal: AbortSignal.timeout(8000),
    });

    if (resp.ok) {
      const xml = await resp.text();
      const items = parseRSSItems(xml);

      // Filter by ticker if specific coin requested
      const tickerUpper = ticker.toUpperCase();
      const coinNames: Record<string, string[]> = {
        BTC: ["bitcoin", "btc"],
        ETH: ["ethereum", "eth"],
        SOL: ["solana", "sol"],
        DOGE: ["dogecoin", "doge"],
        XRP: ["xrp", "ripple"],
      };

      const keywords = coinNames[tickerUpper] || [tickerUpper.toLowerCase()];
      const filtered = items.filter((item) => {
        const titleLower = item.title.toLowerCase();
        return keywords.some((kw) => titleLower.includes(kw));
      });

      const source = filtered.length > 0 ? filtered : items;

      return source.slice(0, maxResults).map((item) => ({
        title: decodeHTMLEntities(item.title),
        url: item.link,
        source: item.source || "cointelegraph.com",
        publishedAt: item.pubDate ? new Date(item.pubDate).toISOString() : new Date().toISOString(),
      }));
    }
  } catch {
    // Fall through to Google News
  }

  // Fallback to Google News
  return fetchGoogleNews(`${ticker} cryptocurrency news`, maxResults);
}

/* ── Market general news ── */
async function fetchMarketNews(maxResults: number = 10): Promise<NewsItem[]> {
  return fetchGoogleNews("stock market financial news today", maxResults);
}

/* ── Utility helpers ── */
function decodeHTMLEntities(text: string): string {
  return text
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&#x27;/g, "'")
    .replace(/&#x2F;/g, "/");
}

function extractDomain(url: string): string {
  try {
    const hostname = new URL(url).hostname;
    return hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}

/* ── Route handler ── */
export async function GET(request: NextRequest) {
  try {
    const ticker = request.nextUrl.searchParams.get("ticker");

    if (!ticker) {
      return NextResponse.json(
        { error: "Missing ?ticker= parameter" },
        { status: 400 }
      );
    }

    // Check cache
    const cacheKey = ticker.toLowerCase();
    const hit = cached(cacheKey);
    if (hit) {
      return NextResponse.json(hit);
    }

    let news: NewsItem[];

    if (isMarket(ticker)) {
      news = await fetchMarketNews(10);
    } else if (isCN(ticker)) {
      news = await fetchEastmoneyNews(ticker, 10);
    } else if (isCrypto(ticker)) {
      news = await fetchCryptoNews(ticker, 10);
    } else {
      // US stocks
      news = await fetchGoogleNews(`${ticker} stock`, 10);
    }

    // Store in cache
    cache[cacheKey] = { data: news, ts: Date.now() };

    return NextResponse.json(news);
  } catch {
    // Never crash
    return NextResponse.json([]);
  }
}
