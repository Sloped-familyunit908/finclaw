"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import type { MarketData } from "@/app/types";
import { findTicker } from "@/app/lib/tickers";
import { fmt } from "@/app/lib/utils";

/* ── SVG Sparkline from price data ── */
function Sparkline({ data, color }: { data: number[]; color: string }) {
  const w = 100;
  const h = 32;
  const padding = 2;

  // Need at least 1 point to render anything
  if (data.length === 0) return null;

  // Single data point — render a flat line
  if (data.length === 1) {
    const y = h / 2;
    return (
      <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="block" preserveAspectRatio="none">
        <line x1={padding} y1={y} x2={w - padding} y2={y} stroke={color} strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    );
  }

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const points = data
    .map((v, i) => {
      const x = padding + (i / (data.length - 1)) * (w - 2 * padding);
      const y = h - padding - ((v - min) / range) * (h - 2 * padding);
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg
      width={w}
      height={h}
      viewBox={`0 0 ${w} ${h}`}
      className="block"
      preserveAspectRatio="none"
    >
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/* ── Constants ── */
const STORAGE_KEY = "finclaw_watchlist";
const DEFAULT_WATCHLIST = ["AAPL", "NVDA", "TSLA", "MSFT", "GOOGL", "AMZN", "BTC", "ETH"];
const FEATURED_COUNT = 4;

function isCN(symbol: string): boolean {
  return /\.(SH|SZ)$/i.test(symbol);
}

interface CardData {
  symbol: string;
  name: string;
  price: number;
  change: number;
  sparkline: number[];
  isCn: boolean;
}

export default function FeaturedCards() {
  const router = useRouter();
  const [cards, setCards] = useState<CardData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      // Get watchlist from localStorage
      let watchlist = DEFAULT_WATCHLIST;
      try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored) {
          const parsed = JSON.parse(stored);
          if (Array.isArray(parsed) && parsed.length > 0) {
            watchlist = parsed;
          }
        }
      } catch {
        // ignore
      }

      const featured = watchlist.slice(0, FEATURED_COUNT);

      // Fetch prices and sparkline data in parallel
      const [usData, cnData, cryptoData] = await Promise.all([
        fetch("/api/prices?market=us").then((r) => r.json()).catch(() => []),
        fetch("/api/prices?market=cn").then((r) => r.json()).catch(() => []),
        fetch("/api/prices?market=crypto").then((r) => r.json()).catch(() => []),
      ]);

      const priceMap = new Map<string, MarketData>();
      for (const d of [...usData, ...cnData, ...cryptoData]) {
        if (d && d.asset) priceMap.set(d.asset, d);
      }

      // Fetch any featured tickers not covered by market endpoints
      const missing = featured.filter((sym) => !priceMap.has(sym));
      if (missing.length > 0) {
        try {
          const extra = await fetch(
            `/api/prices?symbols=${encodeURIComponent(missing.join(","))}`
          ).then((r) => r.json()).catch(() => []);
          for (const d of extra) {
            if (d && d.asset) priceMap.set(d.asset, d);
          }
        } catch {
          // ignore
        }
      }

      // Fetch sparkline data for each featured ticker
      const sparklinePromises = featured.map((symbol) =>
        fetch(`/api/history?code=${encodeURIComponent(symbol)}&range=1w`)
          .then((r) => r.json())
          .then((data) => {
            if (Array.isArray(data)) {
              return data.map((bar: { close: number }) => bar.close);
            }
            return [];
          })
          .catch(() => [])
      );

      const sparklines = await Promise.all(sparklinePromises);

      if (cancelled) return;

      const result: CardData[] = featured.map((symbol, i) => {
        const data = priceMap.get(symbol);
        const ticker = findTicker(symbol);
        const cn = isCN(symbol);

        return {
          symbol,
          name: data?.nameCn || ticker?.nameCn || ticker?.name || symbol,
          price: data?.price ?? 0,
          change: data?.change24h ?? 0,
          sparkline: sparklines[i],
          isCn: cn,
        };
      });

      setCards(result);
      setLoading(false);
    }

    fetchData();
    const interval = setInterval(fetchData, 60_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  if (loading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        {Array.from({ length: FEATURED_COUNT }).map((_, i) => (
          <div
            key={i}
            className="rounded border border-gray-800/60 bg-[#13131a] p-4 animate-pulse"
          >
            <div className="h-3 w-12 bg-gray-800 rounded mb-3" />
            <div className="h-6 w-20 bg-gray-800 rounded mb-2" />
            <div className="h-3 w-14 bg-gray-800 rounded mb-3" />
            <div className="h-8 w-full bg-gray-800/40 rounded" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
      {cards.map((card) => {
        const isUp = card.change >= 0;
        const color = isUp ? "#22c55e" : "#ef4444";
        const fmtPrice =
          card.price > 0
            ? card.isCn
              ? fmt.cny(card.price)
              : fmt.usd(card.price)
            : "--";

        return (
          <button
            key={card.symbol}
            onClick={() =>
              router.push(`/stock/${encodeURIComponent(card.symbol)}`)
            }
            className="rounded border border-gray-800/60 bg-[#13131a] hover:bg-[#161622] hover:border-gray-700/60 transition-all p-4 text-left group"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-mono font-semibold text-gray-400 group-hover:text-gray-200 transition-colors">
                {card.symbol}
              </span>
              <span
                className={`text-[10px] font-mono font-bold ${
                  isUp ? "text-[#22c55e]" : "text-[#ef4444]"
                }`}
              >
                {card.price > 0
                  ? `${isUp ? "+" : ""}${card.change.toFixed(2)}%`
                  : "--"}
              </span>
            </div>
            <p className="text-lg font-mono font-bold text-gray-100 mb-1">
              {fmtPrice}
            </p>
            <p className="text-[10px] text-gray-600 truncate mb-2">
              {card.name}
            </p>
            {card.sparkline.length > 1 && (
              <Sparkline data={card.sparkline} color={color} />
            )}
          </button>
        );
      })}
    </div>
  );
}
