/* ════════════════════════════════════════════════════════════════
   API ROUTE — /api/fundamentals  — FinClaw
   Fetches fundamental data from Yahoo Finance quoteSummary
   ════════════════════════════════════════════════════════════════ */

import { NextRequest, NextResponse } from "next/server";

export interface FundamentalsData {
  // Valuation
  peRatio: number | null;
  forwardPE: number | null;
  pegRatio: number | null;
  priceToBook: number | null;
  priceToSales: number | null;
  evToEbitda: number | null;
  // Size
  marketCap: number | null;
  enterpriseValue: number | null;
  totalRevenue: number | null;
  // Profitability
  profitMargin: number | null;
  returnOnEquity: number | null;
  revenueGrowth: number | null;
  earningsGrowth: number | null;
  // Dividends & Risk
  dividendYield: number | null;
  beta: number | null;
  fiftyTwoWeekChange: number | null;
  targetMeanPrice: number | null;
}

/* ── Simple in-memory cache (5 min) ── */
const cache: Record<string, { data: FundamentalsData | null; ts: number }> = {};
const CACHE_TTL = 5 * 60_000;

function isCN(code: string) {
  return /\.(SH|SZ)$/i.test(code);
}
function isCrypto(code: string) {
  return ["BTC", "ETH", "SOL"].includes(code.toUpperCase());
}

function extractRaw(obj: Record<string, unknown> | undefined | null, key: string): number | null {
  if (!obj) return null;
  const val = obj[key] as { raw?: number } | undefined;
  if (val && typeof val === "object" && "raw" in val && typeof val.raw === "number") {
    return val.raw;
  }
  return null;
}

async function fetchUSFundamentals(symbol: string): Promise<FundamentalsData | null> {
  try {
    const resp = await fetch(
      `https://query1.finance.yahoo.com/v10/finance/quoteSummary/${symbol}?modules=defaultKeyStatistics,financialData`,
      {
        headers: {
          "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        },
      },
    );

    if (!resp.ok) return null;

    const json = await resp.json();
    const result = json?.quoteSummary?.result?.[0];
    if (!result) return null;

    const stats = result.defaultKeyStatistics as Record<string, unknown> | undefined;
    const fin = result.financialData as Record<string, unknown> | undefined;

    return {
      peRatio: extractRaw(stats, "trailingPE") ?? extractRaw(fin, "trailingPE"),
      forwardPE: extractRaw(stats, "forwardPE"),
      pegRatio: extractRaw(stats, "pegRatio"),
      priceToBook: extractRaw(stats, "priceToBook"),
      priceToSales: extractRaw(stats, "priceToSalesTrailing12Months"),
      evToEbitda: extractRaw(stats, "enterpriseToEbitda"),
      marketCap: extractRaw(stats, "marketCap") ?? extractRaw(fin, "marketCap"),
      enterpriseValue: extractRaw(stats, "enterpriseValue"),
      totalRevenue: extractRaw(fin, "totalRevenue"),
      profitMargin: extractRaw(fin, "profitMargins"),
      returnOnEquity: extractRaw(fin, "returnOnEquity"),
      revenueGrowth: extractRaw(fin, "revenueGrowth"),
      earningsGrowth: extractRaw(fin, "earningsGrowth"),
      dividendYield: extractRaw(stats, "yield") ?? extractRaw(stats, "dividendYield"),
      beta: extractRaw(stats, "beta"),
      fiftyTwoWeekChange: extractRaw(stats, "52WeekChange"),
      targetMeanPrice: extractRaw(fin, "targetMeanPrice"),
    };
  } catch {
    return null;
  }
}

async function fetchCNFundamentals(code: string): Promise<FundamentalsData | null> {
  // Try to get basic PE from Sina finance
  try {
    const num = code.replace(/\.(SH|SZ)$/i, "");
    const exchange = num.startsWith("6") ? "sh" : "sz";
    const resp = await fetch(
      `https://hq.sinajs.cn/list=${exchange}${num}`,
      {
        headers: {
          Referer: "https://finance.sina.com.cn",
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        },
      },
    );
    const buf = await resp.arrayBuffer();
    const decoder = new TextDecoder("gbk");
    const text = decoder.decode(buf);
    const dataStr = text.split('"')[1];
    if (!dataStr) return null;

    const fields = dataStr.split(",");
    const price = parseFloat(fields[3]);
    const eps = parseFloat(fields[34]); // EPS field in Sina format

    if (!isNaN(price) && !isNaN(eps) && eps !== 0) {
      return {
        peRatio: price / eps,
        forwardPE: null,
        pegRatio: null,
        priceToBook: null,
        priceToSales: null,
        evToEbitda: null,
        marketCap: null,
        enterpriseValue: null,
        totalRevenue: null,
        profitMargin: null,
        returnOnEquity: null,
        revenueGrowth: null,
        earningsGrowth: null,
        dividendYield: null,
        beta: null,
        fiftyTwoWeekChange: null,
        targetMeanPrice: null,
      };
    }
    return null;
  } catch {
    return null;
  }
}

export async function GET(request: NextRequest) {
  const code = request.nextUrl.searchParams.get("code");
  if (!code) {
    return NextResponse.json({ error: "Missing code parameter" }, { status: 400 });
  }

  // Crypto has no fundamentals
  if (isCrypto(code)) {
    return NextResponse.json(null);
  }

  // Check cache
  const hit = cache[code];
  if (hit && Date.now() - hit.ts < CACHE_TTL) {
    return NextResponse.json(hit.data);
  }

  let data: FundamentalsData | null;

  if (isCN(code)) {
    data = await fetchCNFundamentals(code);
  } else {
    data = await fetchUSFundamentals(code);
  }

  cache[code] = { data, ts: Date.now() };
  return NextResponse.json(data);
}
