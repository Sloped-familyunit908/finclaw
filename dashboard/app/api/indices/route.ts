/* ════════════════════════════════════════════════════════════════
   API ROUTE — /api/indices  — FinClaw
   Returns major market indices: S&P 500, Nasdaq, Dow, Shanghai
   ════════════════════════════════════════════════════════════════ */

import { NextResponse } from "next/server";

interface IndexData {
  name: string;
  value: number;
  change: number;
  changePct: number;
}

/* ── Simple in-memory cache (60 s) ── */
let cache: { data: IndexData[]; ts: number } | null = null;
const CACHE_TTL = 60_000;

/* ── Fetch US indices from Yahoo Finance ── */
async function fetchYahooIndex(symbol: string, name: string): Promise<IndexData | null> {
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
    const change = price - prevClose;
    const changePct = prevClose > 0 ? (change / prevClose) * 100 : 0;

    return { name, value: price, change, changePct };
  } catch {
    return null;
  }
}

/* ── Fetch Shanghai Composite from Sina ── */
function decodeGBK(buffer: ArrayBuffer): string {
  const decoder = new TextDecoder("gbk");
  return decoder.decode(buffer);
}

async function fetchShanghaiIndex(): Promise<IndexData | null> {
  try {
    const resp = await fetch("https://hq.sinajs.cn/list=s_sh000001", {
      headers: {
        Referer: "https://finance.sina.com.cn",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      },
    });

    const buf = await resp.arrayBuffer();
    const text = decodeGBK(buf);

    // Format: var hq_str_s_sh000001="上证指数,3084.39,17.52,0.57,2868824,34150089";
    // fields: name, current, change, changePct, volume(万手), amount(万元)
    const match = text.match(/"([^"]*)"/);
    if (!match) return null;

    const fields = match[1].split(",");
    if (fields.length < 4) return null;

    const value = parseFloat(fields[1]);
    const change = parseFloat(fields[2]);
    const changePct = parseFloat(fields[3]);

    if (isNaN(value)) return null;

    return { name: "Shanghai", value, change, changePct };
  } catch {
    return null;
  }
}

/* ── Route handler ── */
export async function GET() {
  // Check cache
  if (cache && Date.now() - cache.ts < CACHE_TTL) {
    return NextResponse.json(cache.data);
  }

  const results: IndexData[] = [];

  // Fetch all in parallel
  const [sp500, nasdaq, dow, shanghai] = await Promise.all([
    fetchYahooIndex("%5EGSPC", "S&P 500"),
    fetchYahooIndex("%5EIXIC", "Nasdaq"),
    fetchYahooIndex("%5EDJI", "Dow Jones"),
    fetchShanghaiIndex(),
  ]);

  if (sp500) results.push(sp500);
  if (nasdaq) results.push(nasdaq);
  if (dow) results.push(dow);
  if (shanghai) results.push(shanghai);

  cache = { data: results, ts: Date.now() };
  return NextResponse.json(results);
}
