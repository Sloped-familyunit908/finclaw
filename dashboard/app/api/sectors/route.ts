/* ════════════════════════════════════════════════════════════════
   API ROUTE — /api/sectors  — FinClaw
   Fetches daily change for S&P 500 sector ETFs from Yahoo Finance
   ════════════════════════════════════════════════════════════════ */

import { NextResponse } from "next/server";

export interface SectorData {
  name: string;
  symbol: string;
  change: number;
  weight: number;
}

/* ── S&P 500 sector weights (approximate, fairly stable) ── */
const SECTORS: { name: string; symbol: string; weight: number }[] = [
  { name: "Technology",    symbol: "XLK",  weight: 31.5 },
  { name: "Healthcare",    symbol: "XLV",  weight: 12.2 },
  { name: "Financials",    symbol: "XLF",  weight: 13.1 },
  { name: "Cons. Discr.",  symbol: "XLY",  weight: 10.1 },
  { name: "Communication", symbol: "XLC",  weight: 8.9  },
  { name: "Industrials",   symbol: "XLI",  weight: 8.5  },
  { name: "Cons. Staples", symbol: "XLP",  weight: 5.9  },
  { name: "Energy",        symbol: "XLE",  weight: 3.5  },
  { name: "Utilities",     symbol: "XLU",  weight: 2.4  },
  { name: "Real Estate",   symbol: "XLRE", weight: 2.2  },
  { name: "Materials",     symbol: "XLB",  weight: 1.7  },
];

/* ── Simple in-memory cache (60 s) ── */
let sectorCache: { data: SectorData[]; ts: number } | null = null;
const CACHE_TTL = 60_000;

async function fetchSectorData(): Promise<SectorData[]> {
  const results: SectorData[] = [];

  // Fetch all sector ETFs from Yahoo Finance
  for (const sector of SECTORS) {
    try {
      const resp = await fetch(
        `https://query1.finance.yahoo.com/v8/finance/chart/${sector.symbol}?interval=1d&range=1d`,
        {
          headers: {
            "User-Agent":
              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
          },
        },
      );
      const json = await resp.json();
      const meta = json?.chart?.result?.[0]?.meta;

      if (meta?.regularMarketPrice) {
        const price = meta.regularMarketPrice;
        const prevClose =
          meta.chartPreviousClose ?? meta.previousClose ?? price;
        const change =
          prevClose > 0 ? ((price - prevClose) / prevClose) * 100 : 0;

        results.push({
          name: sector.name,
          symbol: sector.symbol,
          change,
          weight: sector.weight,
        });
      } else {
        results.push({
          name: sector.name,
          symbol: sector.symbol,
          change: 0,
          weight: sector.weight,
        });
      }
    } catch {
      results.push({
        name: sector.name,
        symbol: sector.symbol,
        change: 0,
        weight: sector.weight,
      });
    }
  }

  return results;
}

export async function GET() {
  if (sectorCache && Date.now() - sectorCache.ts < CACHE_TTL) {
    return NextResponse.json(sectorCache.data);
  }

  const data = await fetchSectorData();
  sectorCache = { data, ts: Date.now() };
  return NextResponse.json(data);
}
