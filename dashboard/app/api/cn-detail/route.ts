/* ════════════════════════════════════════════════════════════════
   API ROUTE — /api/cn-detail  — FinClaw
   Enhanced A-share data: fund flow + fundamentals
   Calls Eastmoney APIs directly (same sources AKShare uses)
   60s in-memory cache per stock code
   ════════════════════════════════════════════════════════════════ */

import { NextRequest, NextResponse } from "next/server";

/* ── Types ── */
export interface FundFlowEntry {
  time: string;
  mainNetInflow: number;   // 主力净流入 (CNY)
  smallNetInflow: number;  // 散户净流入 (CNY)
  mainNetInflowPct: number;
  largeNetInflow: number;  // 超大单净流入
  midNetInflow: number;    // 中单净流入
}

export interface CNFundamentals {
  reportDate: string;
  basicEps: number | null;
  totalRevenue: number | null;
  revenueYoyRatio: number | null;
  netProfitYoyRatio: number | null;
  roeWeight: number | null;
}

export interface CNDetailData {
  code: string;
  fundFlow: FundFlowEntry[];
  fundamentals: CNFundamentals[];
  todayMainNetInflow: number | null;
  todayRetailNetInflow: number | null;
}

/* ── Cache ── */
const cache: Record<string, { data: CNDetailData; ts: number }> = {};
const CACHE_TTL = 60_000;

/* ── Helpers ── */
function toSecid(code: string): string {
  // code format: 600438.SH  or  000001.SZ
  const num = code.replace(/\.(SH|SZ)$/i, "");
  const suffix = code.toUpperCase().endsWith(".SH") ? "1" : "0";
  return `${suffix}.${num}`;
}

function toSecucode(code: string): string {
  // Returns e.g. "600438.SH" (already in correct format for Eastmoney filter)
  return code.toUpperCase();
}

/* ── Fetch fund flow from Eastmoney ── */
async function fetchFundFlow(secid: string): Promise<FundFlowEntry[]> {
  try {
    const url =
      `https://push2.eastmoney.com/api/qt/stock/fflow/kline/get?` +
      `secid=${secid}&fields1=f1,f2,f3&fields2=f51,f52,f53,f54,f55&klt=1`;

    const resp = await fetch(url, {
      headers: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        Referer: "https://quote.eastmoney.com",
      },
    });

    const json = await resp.json();
    const klines: string[] = json?.data?.klines ?? [];

    // Each kline is a comma-separated string:
    // time, main_net_inflow, small_net_inflow, main_net_inflow_pct, large_net_inflow, mid_net_inflow
    // Actually the fields depend on fields2 params. With f51-f55:
    // f51=time, f52=main_net_inflow, f53=small_net_inflow, f54=main_net_inflow_pct, f55=large_inflow
    return klines.map((line) => {
      const parts = line.split(",");
      return {
        time: parts[0] ?? "",
        mainNetInflow: parseFloat(parts[1]) || 0,
        smallNetInflow: parseFloat(parts[2]) || 0,
        mainNetInflowPct: parseFloat(parts[3]) || 0,
        largeNetInflow: parseFloat(parts[4]) || 0,
        midNetInflow: 0,
      };
    });
  } catch {
    return [];
  }
}

/* ── Fetch fundamentals from Eastmoney datacenter ── */
async function fetchFundamentals(secucode: string): Promise<CNFundamentals[]> {
  try {
    const url =
      `https://datacenter.eastmoney.com/securities/api/data/v1/get?` +
      `reportName=RPT_F10_FINANCE_MAINFINADATA&` +
      `columns=REPORT_DATE,BASIC_EPS,TOTAL_REVENUE,TOTAL_REVENUE_YOY_RATIO,NET_PROFIT_YOY_RATIO,ROE_WEIGHT&` +
      `filter=(SECUCODE="${secucode}")&` +
      `pageSize=4&sortTypes=-1&sortColumns=REPORT_DATE`;

    const resp = await fetch(url, {
      headers: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        Referer: "https://emweb.eastmoney.com",
      },
    });

    const json = await resp.json();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const rows: any[] = json?.result?.data ?? [];

    return rows.map((row) => ({
      reportDate: row.REPORT_DATE ? row.REPORT_DATE.split(" ")[0] : "",
      basicEps: row.BASIC_EPS ?? null,
      totalRevenue: row.TOTAL_REVENUE ?? null,
      revenueYoyRatio: row.TOTAL_REVENUE_YOY_RATIO ?? null,
      netProfitYoyRatio: row.NET_PROFIT_YOY_RATIO ?? null,
      roeWeight: row.ROE_WEIGHT ?? null,
    }));
  } catch {
    return [];
  }
}

/* ── Route handler ── */
export async function GET(request: NextRequest) {
  const code = request.nextUrl.searchParams.get("code");

  if (!code || !/\.(SH|SZ)$/i.test(code)) {
    return NextResponse.json(
      { error: "Missing or invalid A-share code. Use format: 600438.SH" },
      { status: 400 },
    );
  }

  const cacheKey = code.toUpperCase();
  const cached = cache[cacheKey];
  if (cached && Date.now() - cached.ts < CACHE_TTL) {
    return NextResponse.json(cached.data);
  }

  const secid = toSecid(code);
  const secucode = toSecucode(code);

  const [fundFlow, fundamentals] = await Promise.all([
    fetchFundFlow(secid),
    fetchFundamentals(secucode),
  ]);

  // Compute today's total main force / retail net inflow
  let todayMainNetInflow: number | null = null;
  let todayRetailNetInflow: number | null = null;

  if (fundFlow.length > 0) {
    // Sum all intraday entries (klt=1 gives minute-level data for today)
    const lastEntry = fundFlow[fundFlow.length - 1];
    // The cumulative values are in the last entry
    todayMainNetInflow = lastEntry.mainNetInflow;
    todayRetailNetInflow = lastEntry.smallNetInflow;
  }

  const result: CNDetailData = {
    code: cacheKey,
    fundFlow,
    fundamentals,
    todayMainNetInflow,
    todayRetailNetInflow,
  };

  cache[cacheKey] = { data: result, ts: Date.now() };
  return NextResponse.json(result);
}
