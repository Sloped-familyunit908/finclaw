/* ════════════════════════════════════════════════════════════════
   API ROUTE — /api/prices  — FinClaw
   Fetches real-time prices for CN / US / Crypto markets
   Falls back to mock data on any error
   ════════════════════════════════════════════════════════════════ */

import { NextRequest, NextResponse } from "next/server";
import type { MarketData } from "@/app/types";
import { CN_MARKET_DATA, US_MARKET_DATA, MARKET_DATA } from "@/app/lib/fallbackData";

/* ── Simple in-memory cache (60 s) ── */
const cache: Record<string, { data: MarketData[]; ts: number }> = {};
const CACHE_TTL = 60_000;

function cached(key: string): MarketData[] | null {
  const entry = cache[key];
  if (entry && Date.now() - entry.ts < CACHE_TTL) return entry.data;
  return null;
}

/* ── A-share helpers ── */
function cnSecid(code: string): string {
  const num = code.replace(/\.(SH|SZ)$/i, "");
  if (num.startsWith("6")) return `1.${num}`;
  return `0.${num}`;
}

function cnExchange(code: string): string {
  const num = code.replace(/\.(SH|SZ)$/i, "");
  return num.startsWith("6") ? "sh" : "sz";
}

// Sina API response is GBK-encoded — decode manually
function decodeGBK(buffer: ArrayBuffer): string {
  const decoder = new TextDecoder("gbk");
  return decoder.decode(buffer);
}

async function fetchCNPrices(): Promise<MarketData[]> {
  const codes = CN_MARKET_DATA.map((m) => m.asset);
  const results: MarketData[] = [];

  // Batch fetch from Sina
  const sinaList = codes.map((c) => {
    const num = c.replace(/\.(SH|SZ)$/i, "");
    return `${cnExchange(c)}${num}`;
  }).join(",");

  try {
    const resp = await fetch(`https://hq.sinajs.cn/list=${sinaList}`, {
      headers: {
        Referer: "https://finance.sina.com.cn",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      },
    });

    const buf = await resp.arrayBuffer();
    const text = decodeGBK(buf);
    const lines = text.split("\n").filter((l) => l.trim());

    for (let i = 0; i < codes.length; i++) {
      const code = codes[i];
      const mock = CN_MARKET_DATA[i];
      const line = lines[i];

      if (!line || !line.includes('"')) {
        results.push(mock);
        continue;
      }

      const dataStr = line.split('"')[1];
      if (!dataStr) {
        results.push(mock);
        continue;
      }

      const fields = dataStr.split(",");
      // fields: 0=name, 1=open, 2=prevClose, 3=current, 4=high, 5=low, ...
      // 8=volume(shares), 9=amount(CNY)
      const name = fields[0];
      const prevClose = parseFloat(fields[2]);
      const price = parseFloat(fields[3]);
      const volume = parseFloat(fields[9]); // turnover in CNY

      if (isNaN(price) || price === 0) {
        results.push(mock);
        continue;
      }

      const change24h = prevClose > 0 ? ((price - prevClose) / prevClose) * 100 : 0;

      results.push({
        asset: code,
        nameCn: name || mock.nameCn,
        price,
        change24h,
        volume24h: isNaN(volume) ? mock.volume24h : volume,
        marketCap: null, // Sina API doesn't provide market cap; omit rather than fake
        market: "A股",
      });
    }
  } catch {
    return CN_MARKET_DATA;
  }

  return results.length > 0 ? results : CN_MARKET_DATA;
}

/* ── US stock helpers (Yahoo Finance) ── */
async function fetchUSPrices(): Promise<MarketData[]> {
  const symbols = US_MARKET_DATA.map((m) => m.asset);
  const results: MarketData[] = [];

  for (const symbol of symbols) {
    try {
      const resp = await fetch(
        `https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?interval=1d&range=1d`,
        {
          headers: {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
          },
        },
      );
      const json = await resp.json();
      const meta = json?.chart?.result?.[0]?.meta;

      if (!meta?.regularMarketPrice) {
        const mock = US_MARKET_DATA.find((m) => m.asset === symbol);
        if (mock) results.push(mock);
        continue;
      }

      const price = meta.regularMarketPrice;
      const prevClose = meta.chartPreviousClose ?? meta.previousClose ?? price;
      const change = prevClose > 0 ? ((price - prevClose) / prevClose) * 100 : 0;
      const mock = US_MARKET_DATA.find((m) => m.asset === symbol)!;

      // Try to get market cap from chart meta first
      let marketCap = meta.marketCap ?? null;

      // If chart API doesn't provide marketCap, try quoteSummary
      if (!marketCap) {
        try {
          const summaryResp = await fetch(
            `https://query1.finance.yahoo.com/v10/finance/quoteSummary/${symbol}?modules=price`,
            {
              headers: {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
              },
            },
          );
          const summaryJson = await summaryResp.json();
          marketCap = summaryJson?.quoteSummary?.result?.[0]?.price?.marketCap?.raw ?? null;
        } catch {
          // Ignore — marketCap stays null
        }
      }

      // If still null, estimate from shares outstanding (approximate, updated periodically)
      if (!marketCap) {
        const SHARES_OUTSTANDING: Record<string, number> = {
          AAPL: 15.115e9, MSFT: 7.432e9, GOOGL: 5.882e9, GOOG: 5.882e9,
          AMZN: 10.494e9, NVDA: 24.490e9, META: 2.533e9, TSLA: 3.211e9,
        };
        const shares = SHARES_OUTSTANDING[symbol];
        if (shares && price) {
          marketCap = Math.round(shares * price);
        }
      }

      results.push({
        asset: symbol,
        price,
        change24h: change,
        volume24h: meta.regularMarketVolume ?? mock.volume24h,
        marketCap,
        market: "US",
      });
    } catch {
      const mock = US_MARKET_DATA.find((m) => m.asset === symbol);
      if (mock) results.push(mock);
    }
  }

  return results.length > 0 ? results : US_MARKET_DATA;
}

/* ── Crypto helpers (CoinGecko) ── */
const CRYPTO_IDS: Record<string, string> = {
  BTC: "bitcoin",
  ETH: "ethereum",
  SOL: "solana",
};

async function fetchCryptoPrices(): Promise<MarketData[]> {
  try {
    const ids = Object.values(CRYPTO_IDS).join(",");
    const resp = await fetch(
      `https://api.coingecko.com/api/v3/simple/price?ids=${ids}&vs_currencies=usd&include_24hr_change=true&include_market_cap=true&include_24hr_vol=true`,
      {
        headers: { "User-Agent": "FinClaw/1.0" },
      },
    );
    const json = await resp.json();
    const results: MarketData[] = [];

    for (const [symbol, id] of Object.entries(CRYPTO_IDS)) {
      const d = json[id];
      const mock = MARKET_DATA.find((m) => m.asset === symbol)!;
      if (!d?.usd) {
        results.push(mock);
        continue;
      }

      results.push({
        asset: symbol,
        price: d.usd,
        change24h: d.usd_24h_change ?? 0,
        volume24h: d.usd_24h_vol ?? mock.volume24h,
        marketCap: d.usd_market_cap ?? mock.marketCap,
        market: "Crypto",
      });
    }

    return results.length > 0 ? results : MARKET_DATA;
  } catch {
    return MARKET_DATA;
  }
}

/* ── Fetch individual US stock by symbol (for tickers not in preset list) ── */
async function fetchSingleUSPrice(symbol: string): Promise<MarketData | null> {
  try {
    const resp = await fetch(
      `https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?interval=1d&range=1d`,
      {
        headers: {
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        },
      },
    );
    const json = await resp.json();
    const meta = json?.chart?.result?.[0]?.meta;

    if (!meta?.regularMarketPrice) return null;

    const price = meta.regularMarketPrice;
    const prevClose = meta.chartPreviousClose ?? meta.previousClose ?? price;
    const change = prevClose > 0 ? ((price - prevClose) / prevClose) * 100 : 0;

    // Try to get market cap from chart meta
    let marketCap = meta.marketCap ?? null;

    // If chart API doesn't provide marketCap, try quoteSummary
    if (!marketCap) {
      try {
        const summaryResp = await fetch(
          `https://query1.finance.yahoo.com/v10/finance/quoteSummary/${symbol}?modules=price`,
          {
            headers: {
              "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            },
          },
        );
        const summaryJson = await summaryResp.json();
        marketCap = summaryJson?.quoteSummary?.result?.[0]?.price?.marketCap?.raw ?? null;
      } catch {
        // Ignore — marketCap remains null
      }
    }

    return {
      asset: symbol,
      price,
      change24h: change,
      volume24h: meta.regularMarketVolume ?? null,
      marketCap,
      market: "US",
    };
  } catch {
    return null;
  }
}

/* ── Fetch specific symbols (mixed markets) ── */
async function fetchSymbols(symbols: string[]): Promise<MarketData[]> {
  const results: MarketData[] = [];

  for (const symbol of symbols) {
    // Detect market
    if (/\.(SH|SZ)$/i.test(symbol)) {
      // CN stock — fetch via Sina individually
      const cnData = await fetchCNPrices();
      const found = cnData.find((d) => d.asset === symbol);
      if (found) results.push(found);
    } else if (CRYPTO_IDS[symbol.toUpperCase()]) {
      // Crypto — fetch via CoinGecko
      const cryptoData = await fetchCryptoPrices();
      const found = cryptoData.find((d) => d.asset === symbol);
      if (found) results.push(found);
    } else {
      // US stock — fetch individually
      const data = await fetchSingleUSPrice(symbol);
      if (data) {
        results.push(data);
      } else {
        // Return zero-price placeholder so the UI knows the ticker exists
        results.push({
          asset: symbol,
          price: 0,
          change24h: 0,
          volume24h: null,
          marketCap: null,
          market: "US",
        });
      }
    }
  }

  return results;
}

/* ── Route handler ── */
export async function GET(request: NextRequest) {
  const market = request.nextUrl.searchParams.get("market") ?? "cn";
  const symbolsParam = request.nextUrl.searchParams.get("symbols");

  // If symbols param is present, fetch those specific tickers
  if (symbolsParam) {
    const symbols = symbolsParam.split(",").map((s) => s.trim()).filter(Boolean);
    const cacheKey = `symbols:${symbols.sort().join(",")}`;

    const hit = cached(cacheKey);
    if (hit) return NextResponse.json(hit);

    const data = await fetchSymbols(symbols);
    cache[cacheKey] = { data, ts: Date.now() };
    return NextResponse.json(data);
  }

  const hit = cached(market);
  if (hit) {
    return NextResponse.json(hit);
  }

  let data: MarketData[];

  switch (market) {
    case "cn":
      data = await fetchCNPrices();
      break;
    case "us":
      data = await fetchUSPrices();
      break;
    case "crypto":
      data = await fetchCryptoPrices();
      break;
    default:
      data = [];
  }

  cache[market] = { data, ts: Date.now() };
  return NextResponse.json(data);
}
