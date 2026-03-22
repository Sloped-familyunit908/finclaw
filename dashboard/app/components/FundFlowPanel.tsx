"use client";

import { useEffect, useState } from "react";
import type { CNDetailData } from "@/app/api/cn-detail/route";

/* ── Helpers ── */
function fmtCny(n: number): string {
  const abs = Math.abs(n);
  const sign = n >= 0 ? "+" : "-";

  if (abs >= 1e8) return `${sign}\u00a5${(abs / 1e8).toFixed(2)}\u4ebf`;
  if (abs >= 1e4) return `${sign}\u00a5${(abs / 1e4).toFixed(1)}\u4e07`;
  return `${sign}\u00a5${abs.toLocaleString()}`;
}

function fmtPct(n: number | null): string {
  if (n === null || isNaN(n)) return "\u2014";
  return (n >= 0 ? "+" : "") + n.toFixed(2) + "%";
}

/* ── Component ── */
export default function FundFlowPanel({ code }: { code: string }) {
  const [data, setData] = useState<CNDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [hasData, setHasData] = useState(false);

  // Only render for A-share codes
  const isAShare = /\.(SH|SZ)$/i.test(code);

  useEffect(() => {
    if (!isAShare) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setHasData(false);

    fetch(`/api/cn-detail?code=${encodeURIComponent(code)}`)
      .then((r) => r.json())
      .then((json: CNDetailData) => {
        if (
          json &&
          (json.todayMainNetInflow !== null || json.fundamentals?.length > 0)
        ) {
          setData(json);
          setHasData(true);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [code, isAShare]);

  // Don't render at all for non-A-share stocks
  if (!isAShare) return null;

  // Don't render if no data available (graceful degradation)
  if (!loading && !hasData) return null;

  if (loading) {
    return (
      <section className="rounded border border-gray-800/60 bg-[#13131a] p-5">
        <h2 className="text-sm font-semibold text-gray-400 mb-4">
          Capital Flow
        </h2>
        <div className="h-[80px] flex items-center justify-center">
          <div className="animate-spin w-5 h-5 border-2 border-slate-600 border-t-transparent rounded-full" />
        </div>
      </section>
    );
  }

  if (!data) return null;

  const mainInflow = data.todayMainNetInflow;
  const retailInflow = data.todayRetailNetInflow;
  const hasFundFlow = mainInflow !== null && retailInflow !== null;
  const hasFundamentals = data.fundamentals.length > 0;
  const latestFin = hasFundamentals ? data.fundamentals[0] : null;

  return (
    <section className="rounded border border-gray-800/60 bg-[#13131a] p-5">
      {/* Fund Flow Section */}
      {hasFundFlow && (
        <div className="mb-5">
          <h2 className="text-sm font-semibold text-gray-400 mb-3">
            Capital Flow (Today)
          </h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-[11px] text-gray-500">Main Force</span>
              <p
                className={`text-lg font-mono font-bold ${
                  mainInflow! >= 0 ? "text-[#22c55e]" : "text-[#ef4444]"
                }`}
              >
                {fmtCny(mainInflow!)}
              </p>
              <span className="text-[10px] text-gray-600">
                {mainInflow! >= 0 ? "net inflow" : "net outflow"}
              </span>
            </div>
            <div>
              <span className="text-[11px] text-gray-500">Retail</span>
              <p
                className={`text-lg font-mono font-bold ${
                  retailInflow! >= 0 ? "text-[#22c55e]" : "text-[#ef4444]"
                }`}
              >
                {fmtCny(retailInflow!)}
              </p>
              <span className="text-[10px] text-gray-600">
                {retailInflow! >= 0 ? "net inflow" : "net outflow"}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Fundamentals Section */}
      {hasFundamentals && latestFin && (
        <div>
          <h2 className="text-sm font-semibold text-gray-400 mb-3">
            Financial Highlights
            <span className="text-[10px] text-gray-600 font-normal ml-2">
              {latestFin.reportDate}
            </span>
          </h2>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-x-6 gap-y-2 text-sm">
            <div>
              <span className="text-[11px] text-gray-500">EPS</span>
              <p className="font-mono text-gray-300 text-xs">
                {latestFin.basicEps !== null
                  ? `\u00a5${latestFin.basicEps.toFixed(2)}`
                  : "\u2014"}
              </p>
            </div>
            <div>
              <span className="text-[11px] text-gray-500">Revenue</span>
              <p className="font-mono text-gray-300 text-xs">
                {latestFin.totalRevenue !== null
                  ? latestFin.totalRevenue >= 1e8
                    ? `\u00a5${(latestFin.totalRevenue / 1e8).toFixed(1)}\u4ebf`
                    : `\u00a5${(latestFin.totalRevenue / 1e4).toFixed(0)}\u4e07`
                  : "\u2014"}
              </p>
            </div>
            <div>
              <span className="text-[11px] text-gray-500">Revenue YoY</span>
              <p
                className={`font-mono text-xs ${
                  (latestFin.revenueYoyRatio ?? 0) >= 0
                    ? "text-[#22c55e]"
                    : "text-[#ef4444]"
                }`}
              >
                {fmtPct(latestFin.revenueYoyRatio)}
              </p>
            </div>
            <div>
              <span className="text-[11px] text-gray-500">Net Profit YoY</span>
              <p
                className={`font-mono text-xs ${
                  (latestFin.netProfitYoyRatio ?? 0) >= 0
                    ? "text-[#22c55e]"
                    : "text-[#ef4444]"
                }`}
              >
                {fmtPct(latestFin.netProfitYoyRatio)}
              </p>
            </div>
            <div>
              <span className="text-[11px] text-gray-500">ROE</span>
              <p className="font-mono text-gray-300 text-xs">
                {fmtPct(latestFin.roeWeight)}
              </p>
            </div>
          </div>
        </div>
      )}

      <p className="text-[9px] text-gray-700 mt-3 pt-2 border-t border-gray-800/30">
        Data from Eastmoney. Delayed. Not investment advice.
      </p>
    </section>
  );
}
