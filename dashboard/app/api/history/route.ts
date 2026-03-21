/* ════════════════════════════════════════════════════════════════
   API ROUTE — /api/history  — FinClaw
   Returns OHLCV price history for a given stock/crypto
   Supports ?range= param: 1w, 1m, 3m, 6m, 1y, all
   ════════════════════════════════════════════════════════════════ */

import { NextRequest, NextResponse } from "next/server";

export interface HistoryBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

/* ── Range to days mapping ── */
function rangeToDays(range: string | null): number {
  switch (range?.toLowerCase()) {
    case "1w": return 7;
    case "1m": return 30;
    case "3m": return 90;
    case "6m": return 180;
    case "1y": return 365;
    case "all": return 9999;
    default: return 30;
  }
}

/* ── Range to Yahoo Finance range param ── */
function rangeToYahoo(range: string | null): string {
  switch (range?.toLowerCase()) {
    case "1w": return "5d";
    case "1m": return "1mo";
    case "3m": return "3mo";
    case "6m": return "6mo";
    case "1y": return "1y";
    case "all": return "max";
    default: return "1mo";
  }
}

/* ── Range to Eastmoney lmt param ── */
function rangeToEastmoneyLmt(range: string | null): number {
  switch (range?.toLowerCase()) {
    case "1w": return 5;
    case "1m": return 22;
    case "3m": return 66;
    case "6m": return 132;
    case "1y": return 250;
    case "all": return 500;
    default: return 22;
  }
}

/* ── A-share: Eastmoney kline API ── */
async function fetchCNHistory(code: string, range: string | null): Promise<HistoryBar[]> {
  const num = code.replace(/\.(SH|SZ)$/i, "");
  const secid = num.startsWith("6") ? `1.${num}` : `0.${num}`;
  const lmt = rangeToEastmoneyLmt(range);

  const url = `https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=${secid}&fields1=f1,f2,f3&fields2=f51,f52,f53,f54,f55,f56&klt=101&fqt=1&lmt=${lmt}&end=20990101`;

  const resp = await fetch(url, {
    headers: {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      Referer: "https://quote.eastmoney.com",
    },
  });
  const json = await resp.json();
  const klines: string[] = json?.data?.klines ?? [];

  return klines.map((line: string) => {
    const [date, open, close, high, low, volume] = line.split(",");
    return {
      date,
      open: parseFloat(open),
      high: parseFloat(high),
      low: parseFloat(low),
      close: parseFloat(close),
      volume: parseFloat(volume),
    };
  });
}

/* ── US stocks: Yahoo Finance chart API ── */
async function fetchUSHistory(symbol: string, range: string | null): Promise<HistoryBar[]> {
  const yahooRange = rangeToYahoo(range);
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?interval=1d&range=${yahooRange}`;

  const resp = await fetch(url, {
    headers: {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    },
  });
  const json = await resp.json();
  const result = json?.chart?.result?.[0];

  if (!result) return [];

  const timestamps: number[] = result.timestamp ?? [];
  const quote = result.indicators?.quote?.[0];
  if (!quote) return [];

  const bars: HistoryBar[] = [];
  for (let i = 0; i < timestamps.length; i++) {
    const o = quote.open?.[i];
    const h = quote.high?.[i];
    const l = quote.low?.[i];
    const c = quote.close?.[i];
    const v = quote.volume?.[i];

    if (o == null || c == null) continue;

    const d = new Date(timestamps[i] * 1000);
    bars.push({
      date: d.toISOString().slice(0, 10),
      open: o,
      high: h ?? o,
      low: l ?? o,
      close: c,
      volume: v ?? 0,
    });
  }

  return bars;
}

/* ── Crypto: CoinGecko OHLC ── */
const CRYPTO_IDS: Record<string, string> = {
  BTC: "bitcoin",
  ETH: "ethereum",
  SOL: "solana",
};

async function fetchCryptoHistory(symbol: string, range: string | null): Promise<HistoryBar[]> {
  const id = CRYPTO_IDS[symbol.toUpperCase()];
  if (!id) return [];

  const days = rangeToDays(range);
  const cgDays = days > 365 ? 365 : days; // CoinGecko free tier caps at 365

  const url = `https://api.coingecko.com/api/v3/coins/${id}/ohlc?vs_currency=usd&days=${cgDays}`;
  const resp = await fetch(url, {
    headers: { "User-Agent": "FinClaw/1.0" },
  });
  const data: number[][] = await resp.json();

  if (!Array.isArray(data)) return [];

  return data.map(([ts, open, high, low, close]) => ({
    date: new Date(ts).toISOString().slice(0, 10),
    open,
    high,
    low,
    close,
    volume: 0,
  }));
}

/* ── Detect market type from code ── */
function detectMarket(code: string): "cn" | "us" | "crypto" {
  if (/\.(SH|SZ)$/i.test(code)) return "cn";
  if (CRYPTO_IDS[code.toUpperCase()]) return "crypto";
  return "us";
}

/* ── Route handler ── */
export async function GET(request: NextRequest) {
  const code = request.nextUrl.searchParams.get("code");
  const range = request.nextUrl.searchParams.get("range");
  // Legacy: also support ?days= for backward compatibility
  const daysParam = request.nextUrl.searchParams.get("days");

  if (!code) {
    return NextResponse.json({ error: "Missing ?code= parameter" }, { status: 400 });
  }

  // If legacy days param is used and no range, convert
  const effectiveRange = range || (daysParam ? null : "1m");

  try {
    const market = detectMarket(code);
    let history: HistoryBar[];

    switch (market) {
      case "cn":
        history = await fetchCNHistory(code, effectiveRange);
        break;
      case "us":
        history = await fetchUSHistory(code, effectiveRange);
        break;
      case "crypto":
        history = await fetchCryptoHistory(code, effectiveRange);
        break;
    }

    // If legacy days param, slice
    if (daysParam && !range) {
      const days = Math.min(parseInt(daysParam), 365);
      history = history.slice(-days);
    }

    return NextResponse.json(history);
  } catch (err) {
    return NextResponse.json(
      { error: "Failed to fetch history", detail: String(err) },
      { status: 500 },
    );
  }
}
