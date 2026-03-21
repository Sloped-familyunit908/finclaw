"use client";

import { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import type { MarketData } from "@/app/types";
import {
  US_TICKERS,
  CRYPTO_TICKERS,
} from "@/app/lib/fallbackData";

/* ════════════════════════════════════════════════════════════════
   TOP MOVERS WIDGET — Gainers & Losers
   Shows top 5 gainers and top 5 losers with mini change bars.
   ════════════════════════════════════════════════════════════════ */

export default function TopMovers() {
  const router = useRouter();
  const [allData, setAllData] = useState<MarketData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function fetchAll() {
      setLoading(true);
      const [us, crypto] = await Promise.all([
        fetch("/api/prices?market=us").then((r) => r.json()).catch(() => US_TICKERS),
        fetch("/api/prices?market=crypto").then((r) => r.json()).catch(() => CRYPTO_TICKERS),
      ]);

      if (!cancelled) {
        const combined = [...us, ...crypto].filter(
          (d: MarketData) => d && d.price > 0
        );
        setAllData(combined);
        setLoading(false);
      }
    }

    fetchAll();
    const interval = setInterval(fetchAll, 60_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const { gainers, losers, maxAbsChange } = useMemo(() => {
    const sorted = [...allData].sort((a, b) => b.change24h - a.change24h);
    const g = sorted.slice(0, 5);
    const l = sorted.slice(-5).reverse();
    const all = [...g, ...l];
    const maxAbs = all.reduce((m, d) => Math.max(m, Math.abs(d.change24h)), 1);
    return { gainers: g, losers: l, maxAbsChange: maxAbs };
  }, [allData]);

  const handleClick = (symbol: string) => {
    router.push(`/stock/${encodeURIComponent(symbol)}`);
  };

  const renderList = (items: MarketData[]) => {
    if (loading) {
      return Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex justify-between items-center py-1.5 animate-pulse">
          <div className="h-3 w-16 bg-gray-800 rounded" />
          <div className="h-3 w-12 bg-gray-800 rounded" />
        </div>
      ));
    }

    if (items.length === 0) {
      return (
        <p className="text-[10px] text-gray-600 py-2">No data</p>
      );
    }

    return items.map((item) => {
      const isUp = item.change24h >= 0;
      const barWidth = Math.min(
        (Math.abs(item.change24h) / maxAbsChange) * 100,
        100
      );
      return (
        <button
          key={item.asset}
          className="flex items-center py-1.5 w-full text-left hover:bg-gray-800/40 rounded px-1 -mx-1 transition-colors group"
          onClick={() => handleClick(item.asset)}
        >
          <span className="text-xs text-gray-400 group-hover:text-gray-200 truncate mr-2 font-mono w-14 shrink-0">
            {item.asset}
          </span>
          <div className="flex-1 mx-2 h-3 bg-gray-900/60 rounded-sm overflow-hidden relative">
            <div
              className={`h-full rounded-sm transition-all ${
                isUp ? "bg-[#22c55e]/30" : "bg-[#ef4444]/30"
              }`}
              style={{ width: `${barWidth}%` }}
            />
          </div>
          <span
            className={`text-xs font-mono font-bold shrink-0 w-16 text-right ${
              isUp ? "text-[#22c55e]" : "text-[#ef4444]"
            }`}
          >
            {isUp ? "+" : ""}{item.change24h.toFixed(2)}%
          </span>
        </button>
      );
    });
  };

  return (
    <div className="rounded border border-gray-800/60 bg-[#13131a] p-4">
      <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
        Top Movers
      </h3>
      <div className="space-y-4">
        {/* Gainers */}
        <div>
          <h4 className="text-[10px] font-semibold text-[#22c55e] uppercase tracking-wider mb-1.5 border-b border-gray-800/40 pb-1">
            Gainers
          </h4>
          <div className="space-y-0">
            {renderList(gainers)}
          </div>
        </div>

        {/* Losers */}
        <div>
          <h4 className="text-[10px] font-semibold text-[#ef4444] uppercase tracking-wider mb-1.5 border-b border-gray-800/40 pb-1">
            Losers
          </h4>
          <div className="space-y-0">
            {renderList(losers)}
          </div>
        </div>
      </div>
    </div>
  );
}
