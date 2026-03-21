/* ════════════════════════════════════════════════════════════════
   API ROUTE — /api/screener  — FinClaw
   Aggregates all markets, applies filters, returns sorted results.
   ════════════════════════════════════════════════════════════════ */

import { NextRequest, NextResponse } from "next/server";
import type { MarketData } from "@/app/types";
import { findTicker } from "@/app/lib/tickers";

/* ── In-memory cache (30 s) ── */
interface CacheEntry {
  data: MarketData[];
  ts: number;
}

let allCache: CacheEntry | null = null;
const CACHE_TTL = 30_000;

/* ── Fetch all markets from existing /api/prices ── */
async function fetchAllMarkets(baseUrl: string): Promise<MarketData[]> {
  if (allCache && Date.now() - allCache.ts < CACHE_TTL) {
    return allCache.data;
  }

  const markets = ["cn", "us", "crypto"];
  const results: MarketData[] = [];

  const fetches = markets.map(async (market) => {
    try {
      const resp = await fetch(`${baseUrl}/api/prices?market=${market}`, {
        cache: "no-store",
      });
      if (!resp.ok) return [];
      const data: MarketData[] = await resp.json();
      return Array.isArray(data) ? data : [];
    } catch {
      return [];
    }
  });

  const batches = await Promise.all(fetches);
  for (const batch of batches) {
    results.push(...batch);
  }

  allCache = { data: results, ts: Date.now() };
  return results;
}

/* ── Normalize market labels ── */
function normalizeMarketFilter(market: string): string[] {
  switch (market.toLowerCase()) {
    case "us":
      return ["US"];
    case "cn":
      return ["A股"];
    case "crypto":
      return ["Crypto"];
    case "all":
    default:
      return ["US", "A股", "Crypto"];
  }
}

/* ── Route handler ── */
export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;

  // Build base URL from the request
  const proto = request.headers.get("x-forwarded-proto") ?? "http";
  const host = request.headers.get("host") ?? "localhost:3000";
  const baseUrl = `${proto}://${host}`;

  // Parse filter params
  const market = searchParams.get("market") ?? "all";
  const priceMin = parseFloat(searchParams.get("priceMin") ?? "");
  const priceMax = parseFloat(searchParams.get("priceMax") ?? "");
  const changeMin = parseFloat(searchParams.get("changeMin") ?? "");
  const changeMax = parseFloat(searchParams.get("changeMax") ?? "");
  const volumeMin = parseFloat(searchParams.get("volumeMin") ?? "");
  const volumeMax = parseFloat(searchParams.get("volumeMax") ?? "");
  const sortBy = searchParams.get("sort") ?? "change";
  const order = searchParams.get("order") ?? "desc";

  try {
    let data = await fetchAllMarkets(baseUrl);

    // Filter by market
    const allowedMarkets = normalizeMarketFilter(market);
    data = data.filter((d) => d.market && allowedMarkets.includes(d.market));

    // Filter by price
    if (!isNaN(priceMin)) {
      data = data.filter((d) => d.price >= priceMin);
    }
    if (!isNaN(priceMax)) {
      data = data.filter((d) => d.price <= priceMax);
    }

    // Filter by change%
    if (!isNaN(changeMin)) {
      data = data.filter((d) => d.change24h >= changeMin);
    }
    if (!isNaN(changeMax)) {
      data = data.filter((d) => d.change24h <= changeMax);
    }

    // Filter by volume
    if (!isNaN(volumeMin)) {
      data = data.filter((d) => d.volume24h !== null && d.volume24h >= volumeMin);
    }
    if (!isNaN(volumeMax)) {
      data = data.filter((d) => d.volume24h !== null && d.volume24h <= volumeMax);
    }

    // Remove entries with zero price (unfetched fallback)
    data = data.filter((d) => d.price > 0);

    // Enrich with ticker info (name)
    const enriched = data.map((d) => {
      const ticker = findTicker(d.asset);
      return {
        ...d,
        name: d.nameCn || ticker?.name || d.asset,
        nameCn: d.nameCn || ticker?.nameCn,
      };
    });

    // Sort
    const sortMultiplier = order === "asc" ? 1 : -1;
    enriched.sort((a, b) => {
      let va: number;
      let vb: number;
      switch (sortBy) {
        case "price":
          va = a.price;
          vb = b.price;
          break;
        case "change":
          va = a.change24h;
          vb = b.change24h;
          break;
        case "volume":
          va = a.volume24h ?? 0;
          vb = b.volume24h ?? 0;
          break;
        case "marketCap":
          va = a.marketCap ?? 0;
          vb = b.marketCap ?? 0;
          break;
        case "ticker":
          return sortMultiplier * a.asset.localeCompare(b.asset);
        case "name":
          return sortMultiplier * (a.name ?? "").localeCompare(b.name ?? "");
        default:
          va = a.change24h;
          vb = b.change24h;
      }
      return sortMultiplier * (va - vb);
    });

    return NextResponse.json({
      total: enriched.length,
      data: enriched,
    });
  } catch {
    return NextResponse.json(
      { error: "Failed to fetch screener data. Please try again." },
      { status: 500 },
    );
  }
}
