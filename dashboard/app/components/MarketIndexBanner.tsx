"use client";

import { useState, useEffect } from "react";

interface IndexData {
  name: string;
  value: number;
  change: number;
  changePct: number;
}

export default function MarketIndexBanner() {
  const [indices, setIndices] = useState<IndexData[]>([]);
  const [btc, setBtc] = useState<IndexData | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const [indicesResp, cryptoResp] = await Promise.all([
          fetch("/api/indices").then((r) => r.json()).catch(() => []),
          fetch("/api/prices?market=crypto").then((r) => r.json()).catch(() => []),
        ]);

        if (Array.isArray(indicesResp)) {
          setIndices(indicesResp);
        }

        // Extract BTC from crypto data
        if (Array.isArray(cryptoResp)) {
          const btcData = cryptoResp.find(
            (c: { asset: string }) => c.asset === "BTC"
          );
          if (btcData && btcData.price > 0) {
            setBtc({
              name: "BTC",
              value: btcData.price,
              change: 0,
              changePct: btcData.change24h ?? 0,
            });
          }
        }
      } catch {
        // Silently fail — banner is supplementary
      }
    }

    fetchData();
    const interval = setInterval(fetchData, 60_000);
    return () => clearInterval(interval);
  }, []);

  const allItems = [...indices, ...(btc ? [btc] : [])];

  if (allItems.length === 0) return null;

  return (
    <div className="border-b border-gray-800/40 bg-[#0d0d14] px-4 py-1.5 overflow-x-auto scrollbar-hide">
      <div className="max-w-7xl mx-auto flex items-center gap-4 text-xs font-mono whitespace-nowrap">
        {allItems.map((item, i) => {
          const isUp = item.changePct >= 0;
          return (
            <span key={item.name} className="flex items-center gap-1.5">
              {i > 0 && (
                <span className="text-gray-700 mr-1.5">|</span>
              )}
              <span className="text-gray-400">{item.name}</span>
              <span className="text-gray-200">
                {item.name === "BTC"
                  ? `$${item.value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
                  : item.value.toLocaleString(undefined, { maximumFractionDigits: 2 })}
              </span>
              <span
                className={`font-bold ${isUp ? "text-green-400" : "text-red-400"}`}
              >
                {isUp ? "+" : ""}
                {item.changePct.toFixed(2)}%
              </span>
            </span>
          );
        })}
      </div>
    </div>
  );
}
