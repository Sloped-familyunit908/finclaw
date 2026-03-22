/* ════════════════════════════════════════════════════════════════
   API ROUTE — /api/crypto  — FinClaw
   Fetches top 20 cryptos by market cap from CoinGecko
   Supports optional ?pairs=BTC,ETH,SOL filter
   60s in-memory cache
   ════════════════════════════════════════════════════════════════ */

import { NextRequest, NextResponse } from "next/server";

/* ── Types ── */
export interface CryptoMarketItem {
  rank: number;
  id: string;
  symbol: string;
  name: string;
  image: string;
  price: number;
  change24h: number;
  marketCap: number;
  volume24h: number;
  high24h: number;
  low24h: number;
  circulatingSupply: number | null;
  totalSupply: number | null;
  ath: number;
  athChangePercentage: number;
}

/* ── Cache ── */
let cachedData: CryptoMarketItem[] | null = null;
let cacheTs = 0;
const CACHE_TTL = 60_000; // 60s

/* ── Fetch from CoinGecko /coins/markets ── */
async function fetchTopCryptos(): Promise<CryptoMarketItem[]> {
  const now = Date.now();
  if (cachedData && now - cacheTs < CACHE_TTL) {
    return cachedData;
  }

  const url =
    "https://api.coingecko.com/api/v3/coins/markets?" +
    "vs_currency=usd&order=market_cap_desc&per_page=20&page=1&sparkline=false";

  const resp = await fetch(url, {
    headers: { "User-Agent": "FinClaw/1.0" },
    next: { revalidate: 60 },
  });

  if (!resp.ok) {
    // If rate-limited or error, return stale cache if available
    if (cachedData) return cachedData;
    throw new Error(`CoinGecko API returned ${resp.status}`);
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const json: any[] = await resp.json();

  const items: CryptoMarketItem[] = json.map((coin, idx) => ({
    rank: idx + 1,
    id: coin.id,
    symbol: (coin.symbol as string).toUpperCase(),
    name: coin.name,
    image: coin.image ?? "",
    price: coin.current_price ?? 0,
    change24h: coin.price_change_percentage_24h ?? 0,
    marketCap: coin.market_cap ?? 0,
    volume24h: coin.total_volume ?? 0,
    high24h: coin.high_24h ?? 0,
    low24h: coin.low_24h ?? 0,
    circulatingSupply: coin.circulating_supply ?? null,
    totalSupply: coin.total_supply ?? null,
    ath: coin.ath ?? 0,
    athChangePercentage: coin.ath_change_percentage ?? 0,
  }));

  cachedData = items;
  cacheTs = now;
  return items;
}

/* ── Route handler ── */
export async function GET(request: NextRequest) {
  try {
    const allCryptos = await fetchTopCryptos();

    // Optional filtering by pairs
    const pairsParam = request.nextUrl.searchParams.get("pairs");
    if (pairsParam) {
      const wanted = new Set(
        pairsParam
          .split(",")
          .map((s) => s.trim().toUpperCase())
          .filter(Boolean),
      );
      const filtered = allCryptos.filter((c) => wanted.has(c.symbol));
      return NextResponse.json(filtered);
    }

    return NextResponse.json(allCryptos);
  } catch (err) {
    console.error("[/api/crypto] Error:", err);
    return NextResponse.json([], { status: 502 });
  }
}
