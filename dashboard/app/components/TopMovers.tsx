"use client";

import { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import type { MarketData } from "@/app/types";
import {
  US_TICKERS,
  CN_TICKERS,
  CRYPTO_TICKERS,
} from "@/app/lib/fallbackData";

/* ════════════════════════════════════════════════════════════════
   TOP MOVERS WIDGET — Gainers & Losers
   Shows top 5 gainers and top 5 losers from all market data.
   ════════════════════════════════════════════════════════════════ */

export default function TopMovers() {
  const router = useRouter();
  const [allData, setAllData] = useState<MarketData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function fetchAll() {
      setLoading(true);
      const [us, cn, crypto] = await Promise.all([
        fetch("/api/prices?market=us").then((r) => r.json()).catch(() => US_TICKERS),
        fetch("/api/prices?market=cn").then((r) => r.json()).catch(() => CN_TICKERS),
        fetch("/api/prices?market=crypto").then((r) => r.json()).catch(() => CRYPTO_TICKERS),
      ]);

      if (!cancelled) {
        const combined = [...us, ...cn, ...crypto].filter(
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

  const { gainers, losers } = useMemo(() => {
    const sorted = [...allData].sort((a, b) => b.change24h - a.change24h);
    return {
      gainers: sorted.slice(0, 5),
      losers: sorted.slice(-5).reverse(),
    };
  }, [allData]);

  const handleClick = (symbol: string) => {
    router.push(`/stock/${encodeURIComponent(symbol)}`);
  };

  const renderList = (items: MarketData[], isGainer: boolean) => {
    if (loading) {
      return Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex justify-between items-center py-1 animate-pulse">
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
      const displayName = item.nameCn || item.asset;
      return (
        <button
          key={item.asset}
          className="flex justify-between items-center py-1 w-full text-left hover:bg-gray-800/40 rounded px-1 -mx-1 transition-colors"
          onClick={() => handleClick(item.asset)}
        >
          <span className="text-xs text-gray-300 truncate mr-2 font-mono">
            {displayName}
          </span>
          <span
            className={`text-xs font-mono font-bold shrink-0 ${
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
    <section>
      <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
        Top Movers
      </h2>
      <div className="grid grid-cols-2 gap-4">
        {/* Gainers */}
        <div className="rounded border border-gray-800/60 bg-[#13131a] p-3">
          <h3 className="text-[10px] font-semibold text-[#22c55e] uppercase tracking-wider mb-2 border-b border-gray-800/40 pb-1.5">
            Top Gainers
          </h3>
          <div className="space-y-0.5">
            {renderList(gainers, true)}
          </div>
        </div>

        {/* Losers */}
        <div className="rounded border border-gray-800/60 bg-[#13131a] p-3">
          <h3 className="text-[10px] font-semibold text-[#ef4444] uppercase tracking-wider mb-2 border-b border-gray-800/40 pb-1.5">
            Top Losers
          </h3>
          <div className="space-y-0.5">
            {renderList(losers, false)}
          </div>
        </div>
      </div>
    </section>
  );
}
