"use client";

import { useEffect, useState } from "react";

interface FundamentalsData {
  peRatio: number | null;
  forwardPE: number | null;
  pegRatio: number | null;
  priceToBook: number | null;
  priceToSales: number | null;
  evToEbitda: number | null;
  marketCap: number | null;
  enterpriseValue: number | null;
  totalRevenue: number | null;
  profitMargin: number | null;
  returnOnEquity: number | null;
  revenueGrowth: number | null;
  earningsGrowth: number | null;
  dividendYield: number | null;
  beta: number | null;
  fiftyTwoWeekChange: number | null;
  targetMeanPrice: number | null;
}

function fmtVal(val: number | null, type: "number" | "pct" | "currency" | "compact" = "number"): string {
  if (val === null || val === undefined || isNaN(val)) return "\u2014";

  switch (type) {
    case "pct":
      return (val >= 0 ? "+" : "") + (val * 100).toFixed(1) + "%";
    case "currency":
      return "$" + val.toFixed(2);
    case "compact": {
      const abs = Math.abs(val);
      if (abs >= 1e12) return "$" + (val / 1e12).toFixed(2) + "T";
      if (abs >= 1e9) return "$" + (val / 1e9).toFixed(1) + "B";
      if (abs >= 1e6) return "$" + (val / 1e6).toFixed(1) + "M";
      return "$" + val.toLocaleString();
    }
    default:
      return val.toFixed(2);
  }
}

function Row({
  label,
  value,
  className,
}: {
  label: string;
  value: string;
  className?: string;
}) {
  const isPositive = value.startsWith("+");
  const isNegative = value.startsWith("-") && value !== "\u2014";

  return (
    <div className="flex justify-between items-center py-[3px]">
      <span className="text-[11px] text-gray-500">{label}</span>
      <span
        className={`text-[11px] font-mono text-right ${
          className ??
          (isPositive
            ? "text-[#22c55e]"
            : isNegative
              ? "text-[#ef4444]"
              : "text-gray-300")
        }`}
      >
        {value}
      </span>
    </div>
  );
}

export default function FundamentalsPanel({ code }: { code: string }) {
  const [data, setData] = useState<FundamentalsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [hasData, setHasData] = useState(false);

  useEffect(() => {
    setLoading(true);
    setHasData(false);

    fetch(`/api/fundamentals?code=${encodeURIComponent(code)}`)
      .then((r) => r.json())
      .then((json) => {
        if (json && typeof json === "object" && json.peRatio !== undefined) {
          setData(json);
          setHasData(true);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [code]);

  // Don't render for crypto or when no data
  if (!loading && !hasData) return null;

  if (loading) {
    return (
      <section className="rounded border border-gray-800/60 bg-[#13131a] p-5">
        <h2 className="text-sm font-semibold text-gray-400 mb-4">
          Fundamentals
        </h2>
        <div className="h-[120px] flex items-center justify-center">
          <div className="animate-spin w-5 h-5 border-2 border-slate-600 border-t-transparent rounded-full" />
        </div>
      </section>
    );
  }

  if (!data) return null;

  return (
    <section className="rounded border border-gray-800/60 bg-[#13131a] p-5">
      <h2 className="text-sm font-semibold text-gray-400 mb-4">
        Fundamentals
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-0">
        {/* Left column: Valuation + Size */}
        <div>
          <p className="text-[10px] font-semibold text-gray-600 uppercase tracking-wider mb-1 border-b border-gray-800/40 pb-1">
            Valuation
          </p>
          <Row label="PE (TTM)" value={fmtVal(data.peRatio)} className="text-gray-300" />
          <Row label="Forward PE" value={fmtVal(data.forwardPE)} className="text-gray-300" />
          <Row label="PEG" value={fmtVal(data.pegRatio)} className="text-gray-300" />
          <Row label="P/B" value={fmtVal(data.priceToBook)} className="text-gray-300" />
          <Row label="P/S" value={fmtVal(data.priceToSales)} className="text-gray-300" />
          <Row label="EV/EBITDA" value={fmtVal(data.evToEbitda)} className="text-gray-300" />

          <p className="text-[10px] font-semibold text-gray-600 uppercase tracking-wider mb-1 mt-3 border-b border-gray-800/40 pb-1">
            Size
          </p>
          <Row label="Market Cap" value={fmtVal(data.marketCap, "compact")} className="text-gray-300" />
          <Row label="Revenue" value={fmtVal(data.totalRevenue, "compact")} className="text-gray-300" />
        </div>

        {/* Right column: Profitability + Dividends & Risk */}
        <div>
          <p className="text-[10px] font-semibold text-gray-600 uppercase tracking-wider mb-1 border-b border-gray-800/40 pb-1">
            Profitability
          </p>
          <Row label="Profit Margin" value={fmtVal(data.profitMargin, "pct")} />
          <Row label="ROE" value={fmtVal(data.returnOnEquity, "pct")} />
          <Row label="Revenue Growth" value={fmtVal(data.revenueGrowth, "pct")} />
          <Row label="Earnings Growth" value={fmtVal(data.earningsGrowth, "pct")} />

          <p className="text-[10px] font-semibold text-gray-600 uppercase tracking-wider mb-1 mt-3 border-b border-gray-800/40 pb-1">
            Risk / Income
          </p>
          <Row
            label="Div Yield"
            value={data.dividendYield !== null ? (data.dividendYield * 100).toFixed(2) + "%" : "\u2014"}
            className="text-gray-300"
          />
          <Row
            label="Beta"
            value={data.beta !== null ? data.beta.toFixed(2) : "\u2014"}
            className="text-gray-300"
          />
          <Row label="52w Change" value={fmtVal(data.fiftyTwoWeekChange, "pct")} />
          <Row
            label="Analyst Target"
            value={fmtVal(data.targetMeanPrice, "currency")}
            className="text-gray-300"
          />
        </div>
      </div>

      <p className="text-[9px] text-gray-700 mt-3 pt-2 border-t border-gray-800/30">
        Data from Yahoo Finance. Delayed. Not investment advice.
      </p>
    </section>
  );
}
