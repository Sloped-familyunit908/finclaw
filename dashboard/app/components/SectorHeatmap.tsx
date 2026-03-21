"use client";

import { useEffect, useState } from "react";

interface SectorData {
  name: string;
  symbol: string;
  change: number;
  weight: number;
}

function getChangeColor(change: number): string {
  if (change >= 2) return "bg-[#166534]";
  if (change >= 1) return "bg-[#15803d]";
  if (change >= 0.5) return "bg-[#16a34a]";
  if (change >= 0) return "bg-[#1a3a2a]";
  if (change >= -0.5) return "bg-[#3a1a1a]";
  if (change >= -1) return "bg-[#991b1b]";
  if (change >= -2) return "bg-[#b91c1c]";
  return "bg-[#dc2626]";
}

function getTextColor(change: number): string {
  if (change >= 0.5) return "text-[#86efac]";
  if (change >= 0) return "text-[#4ade80]";
  if (change >= -0.5) return "text-[#fca5a5]";
  return "text-[#f87171]";
}

export default function SectorHeatmap() {
  const [sectors, setSectors] = useState<SectorData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/sectors")
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data)) setSectors(data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <section className="rounded border border-gray-800/60 bg-[#13131a] p-4">
        <h2 className="text-xs font-semibold text-gray-500 tracking-wider uppercase mb-3">
          S&P 500 Sectors
        </h2>
        <div className="h-[180px] flex items-center justify-center">
          <div className="animate-spin w-5 h-5 border-2 border-slate-600 border-t-transparent rounded-full" />
        </div>
      </section>
    );
  }

  if (sectors.length === 0) return null;

  // Build rows for the treemap layout
  // Sort sectors by weight descending for visual balance
  const sorted = [...sectors].sort((a, b) => b.weight - a.weight);
  const totalWeight = sorted.reduce((s, sec) => s + sec.weight, 0);

  return (
    <section className="rounded border border-gray-800/60 bg-[#13131a] p-4">
      <h2 className="text-xs font-semibold text-gray-500 tracking-wider uppercase mb-3">
        S&P 500 Sectors
      </h2>

      <div className="flex flex-wrap gap-[2px]" style={{ height: "180px" }}>
        {sorted.map((sector) => {
          const pct = (sector.weight / totalWeight) * 100;
          const changeStr =
            (sector.change >= 0 ? "+" : "") + sector.change.toFixed(2) + "%";

          return (
            <div
              key={sector.symbol}
              className={`${getChangeColor(sector.change)} rounded-sm flex flex-col items-center justify-center cursor-default transition-opacity hover:opacity-90 overflow-hidden`}
              style={{
                flexBasis: `${Math.max(pct - 0.2, 4)}%`,
                flexGrow: pct > 10 ? 2 : 1,
                minWidth: "50px",
                minHeight: "48px",
              }}
              title={`${sector.name} (${sector.symbol}) ${changeStr}`}
            >
              <span className="text-[10px] text-gray-300 font-medium leading-tight text-center px-1 truncate w-full">
                {sector.name}
              </span>
              <span
                className={`text-xs font-mono font-bold ${getTextColor(sector.change)}`}
              >
                {changeStr}
              </span>
              <span className="text-[9px] text-gray-500 font-mono">
                {sector.symbol}
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
}
