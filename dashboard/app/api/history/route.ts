/* ════════════════════════════════════════════════════════════════
   API ROUTE — /api/history  — FinClaw
   Returns OHLCV price history for a given stock/crypto
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

/* ── A-share: Eastmoney kline API ── */
async function fetchCNHistory(code: string, days: number): Promise<HistoryBar[]> {
  const num = code.replace(/\.(SH|SZ)$/i, "");
  const secid = num.startsWith("6") ? `1.${num}` : `0.${num}`;

  const url = `https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=${secid}&fields1=f1,f2,f3&fields2=f51,f52,f53,f54,f55,f56&klt=101&fqt=1&lmt=${days}&end=20990101`;

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
async function fetchUSHistory(symbol: string, days: number): Promise<HistoryBar[]> {
  const range = days <= 5 ? "5d" : days <= 30 ? "1mo" : days <= 90 ? "3mo" : "6mo";
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?interval=1d&range=${range}`;

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

  return bars.slice(-days);
}

/* ── Crypto: CoinGecko OHLC ── */
const CRYPTO_IDS: Record<string, string> = {
  BTC: "bitcoin",
  ETH: "ethereum",
  SOL: "solana",
};

async function fetchCryptoHistory(symbol: string, days: number): Promise<HistoryBar[]> {
  const id = CRYPTO_IDS[symbol.toUpperCase()];
  if (!id) return [];

  const url = `https://api.coingecko.com/api/v3/coins/${id}/ohlc?vs_currency=usd&days=${days}`;
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
    volume: 0, // CoinGecko OHLC doesn't include volume
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
  const days = Math.min(parseInt(request.nextUrl.searchParams.get("days") ?? "30"), 365);

  if (!code) {
    return NextResponse.json({ error: "Missing ?code= parameter" }, { status: 400 });
  }

  try {
    const market = detectMarket(code);
    let history: HistoryBar[];

    switch (market) {
      case "cn":
        history = await fetchCNHistory(code, days);
        break;
      case "us":
        history = await fetchUSHistory(code, days);
        break;
      case "crypto":
        history = await fetchCryptoHistory(code, days);
        break;
    }

    return NextResponse.json(history);
  } catch (err) {
    return NextResponse.json(
      { error: "Failed to fetch history", detail: String(err) },
      { status: 500 },
    );
  }
}
