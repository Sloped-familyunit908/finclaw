"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import type { TabId, MarketData } from "@/app/types";
import {
  CRYPTO_TICKERS,
  US_TICKERS,
  CN_TICKERS,
} from "@/app/lib/fallbackData";
import { fmt } from "@/app/lib/utils";

import Header from "@/app/components/Header";
import PriceCard from "@/app/components/PriceCard";
import BacktestTable from "@/app/components/BacktestTable";
import StrategyGallery from "@/app/components/StrategyGallery";
import CNScanner from "@/app/components/CNScanner";
import MarketIndexBanner from "@/app/components/MarketIndexBanner";

/* -- View mode -- */
type ViewMode = "table" | "cards";

/* -- Sort config -- */
type SortField = "asset" | "price" | "change24h" | "volume24h" | "marketCap";
type SortDir = "asc" | "desc";

/* -- Loading skeleton for price cards -- */
function PriceCardSkeleton() {
  return (
    <div className="rounded border border-gray-800/60 bg-[#13131a] px-3 py-2.5 animate-pulse">
      <div className="flex justify-between items-start mb-1.5">
        <div className="flex-1">
          <div className="h-4 w-24 bg-gray-800 rounded mb-1" />
          <div className="h-3 w-16 bg-gray-800/60 rounded" />
        </div>
        <div className="h-6 w-18 bg-gray-800 rounded" />
      </div>
      <div className="h-7 w-28 bg-gray-800 rounded mb-2" />
      <div className="flex justify-between">
        <div className="h-3 w-20 bg-gray-800/60 rounded" />
        <div className="h-3 w-20 bg-gray-800/60 rounded" />
      </div>
    </div>
  );
}

/* -- Table skeleton -- */
function TableSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div className="overflow-x-auto rounded border border-gray-800/60">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-900/50 text-gray-400 text-xs uppercase tracking-wider">
            <th className="text-left py-3 px-4">Ticker</th>
            <th className="text-right py-3 px-3">Last</th>
            <th className="text-right py-3 px-3">Chg%</th>
            <th className="text-right py-3 px-3 hidden sm:table-cell">Volume</th>
            <th className="text-right py-3 px-3 hidden md:table-cell">Mkt Cap</th>
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, i) => (
            <tr key={i} className="border-t border-gray-800/30 animate-pulse">
              <td className="py-2.5 px-4"><div className="h-4 w-20 bg-gray-800 rounded" /></td>
              <td className="py-2.5 px-3 text-right"><div className="h-4 w-16 bg-gray-800 rounded ml-auto" /></td>
              <td className="py-2.5 px-3 text-right"><div className="h-4 w-14 bg-gray-800 rounded ml-auto" /></td>
              <td className="py-2.5 px-3 text-right hidden sm:table-cell"><div className="h-4 w-16 bg-gray-800 rounded ml-auto" /></td>
              <td className="py-2.5 px-3 text-right hidden md:table-cell"><div className="h-4 w-16 bg-gray-800 rounded ml-auto" /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Filter market data by search query (matches ticker or Chinese name) */
function filterBySearch(data: MarketData[], query: string): MarketData[] {
  if (!query.trim()) return data;
  const q = query.trim().toLowerCase();
  return data.filter(
    (m) =>
      m.asset.toLowerCase().includes(q) ||
      (m.nameCn && m.nameCn.includes(q))
  );
}

/** Sort market data */
function sortData(data: MarketData[], field: SortField, dir: SortDir): MarketData[] {
  return [...data].sort((a, b) => {
    let va: number | string;
    let vb: number | string;

    switch (field) {
      case "asset":
        va = a.nameCn || a.asset;
        vb = b.nameCn || b.asset;
        return dir === "asc"
          ? String(va).localeCompare(String(vb))
          : String(vb).localeCompare(String(va));
      case "price":
        va = a.price;
        vb = b.price;
        break;
      case "change24h":
        va = a.change24h;
        vb = b.change24h;
        break;
      case "volume24h":
        va = a.volume24h ?? 0;
        vb = b.volume24h ?? 0;
        break;
      case "marketCap":
        va = a.marketCap ?? 0;
        vb = b.marketCap ?? 0;
        break;
      default:
        return 0;
    }

    return dir === "asc" ? (va as number) - (vb as number) : (vb as number) - (va as number);
  });
}

/* -- Sortable table header -- */
function SortHeader({
  label,
  field,
  currentField,
  currentDir,
  onSort,
  className = "",
}: {
  label: string;
  field: SortField;
  currentField: SortField;
  currentDir: SortDir;
  onSort: (field: SortField) => void;
  className?: string;
}) {
  const isActive = currentField === field;
  return (
    <th
      className={`py-3 px-3 cursor-pointer select-none hover:text-gray-200 transition-colors ${className}`}
      onClick={() => onSort(field)}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        {isActive && (
          <span className="text-[10px]">{currentDir === "asc" ? "▲" : "▼"}</span>
        )}
      </span>
    </th>
  );
}

/* -- Stock table -- */
function StockTable({
  data,
  searchQuery,
}: {
  data: MarketData[];
  searchQuery: string;
}) {
  const [sortField, setSortField] = useState<SortField>("change24h");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("desc");
    }
  };

  const sorted = useMemo(() => sortData(data, sortField, sortDir), [data, sortField, sortDir]);

  if (data.length === 0) {
    return (
      <p className="text-xs text-gray-600 py-4">
        No tickers match &quot;{searchQuery}&quot;
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded border border-gray-800/60">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-900/50 text-gray-400 text-xs uppercase tracking-wider">
            <SortHeader label="Ticker" field="asset" currentField={sortField} currentDir={sortDir} onSort={handleSort} className="text-left px-4" />
            <SortHeader label="Last" field="price" currentField={sortField} currentDir={sortDir} onSort={handleSort} className="text-right" />
            <SortHeader label="Chg%" field="change24h" currentField={sortField} currentDir={sortDir} onSort={handleSort} className="text-right" />
            <SortHeader label="Volume" field="volume24h" currentField={sortField} currentDir={sortDir} onSort={handleSort} className="text-right hidden sm:table-cell" />
            <SortHeader label="Mkt Cap" field="marketCap" currentField={sortField} currentDir={sortDir} onSort={handleSort} className="text-right hidden md:table-cell" />
          </tr>
        </thead>
        <tbody>
          {sorted.map((m) => {
            const isUp = m.change24h >= 0;
            const isCn = m.market === "A股";
            const fmtPrice = isCn ? fmt.cny(m.price) : fmt.usd(m.price);
            const fmtVol = m.volume24h
              ? isCn
                ? fmt.compactCn(m.volume24h)
                : fmt.compact(m.volume24h)
              : "—";
            const fmtCap = m.marketCap
              ? isCn
                ? fmt.compactCn(m.marketCap)
                : fmt.compact(m.marketCap)
              : "—";

            return (
              <tr
                key={m.asset}
                className="border-t border-gray-800/30 hover:bg-gray-900/30 transition-colors"
              >
                <td className="py-2 px-4">
                  <Link
                    href={`/stock/${encodeURIComponent(m.asset)}`}
                    className="hover:text-white transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-gray-100">
                        {m.nameCn || m.asset}
                      </span>
                      {m.nameCn && (
                        <span className="text-xs text-gray-500 font-mono">
                          {m.asset}
                        </span>
                      )}
                      {m.market && (
                        <span className="px-1 py-0.5 text-[9px] rounded bg-gray-800/60 text-gray-500">
                          {m.market}
                        </span>
                      )}
                    </div>
                  </Link>
                </td>
                <td className="py-2 px-3 text-right font-mono text-gray-200">
                  {fmtPrice}
                </td>
                <td
                  className={`py-2 px-3 text-right font-mono font-bold ${
                    isUp ? "text-green-400" : "text-red-400"
                  }`}
                >
                  {isUp ? "+" : ""}
                  {m.change24h.toFixed(2)}%
                </td>
                <td className="py-2 px-3 text-right font-mono text-gray-400 hidden sm:table-cell">
                  {fmtVol}
                </td>
                <td className="py-2 px-3 text-right font-mono text-gray-400 hidden md:table-cell">
                  {fmtCap}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function Home() {
  const [tab, setTab] = useState<TabId>("overview");
  const [searchQuery, setSearchQuery] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>("table");

  const [usData, setUsData] = useState<MarketData[]>(US_TICKERS);
  const [cnData, setCnData] = useState<MarketData[]>(CN_TICKERS);
  const [cryptoData, setCryptoData] = useState<MarketData[]>(CRYPTO_TICKERS);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function fetchAll() {
      setLoading(true);

      const fetchers = [
        fetch("/api/prices?market=us")
          .then((r) => r.json())
          .catch(() => US_TICKERS),
        fetch("/api/prices?market=cn")
          .then((r) => r.json())
          .catch(() => CN_TICKERS),
        fetch("/api/prices?market=crypto")
          .then((r) => r.json())
          .catch(() => CRYPTO_TICKERS),
      ];

      const [us, cn, crypto] = await Promise.all(fetchers);

      if (!cancelled) {
        setUsData(us);
        setCnData(cn);
        setCryptoData(crypto);
        setLoading(false);
      }
    }

    fetchAll();

    // Refresh every 60 seconds
    const interval = setInterval(fetchAll, 60_000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  // Apply search filter
  const filteredUs = useMemo(() => filterBySearch(usData, searchQuery), [usData, searchQuery]);
  const filteredCn = useMemo(() => filterBySearch(cnData, searchQuery), [cnData, searchQuery]);
  const filteredCrypto = useMemo(() => filterBySearch(cryptoData, searchQuery), [cryptoData, searchQuery]);

  const renderCards = (data: MarketData[]) => {
    if (data.length === 0) {
      return (
        <p className="text-xs text-gray-600 py-4">
          No tickers match &quot;{searchQuery}&quot;
        </p>
      );
    }
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {data.map((m) => (
          <PriceCard key={m.asset} data={m} />
        ))}
      </div>
    );
  };

  const renderSkeletons = (n: number) => (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: n }).map((_, i) => (
        <PriceCardSkeleton key={i} />
      ))}
    </div>
  );

  const renderSection = (title: string, data: MarketData[], skeletonCount: number) => (
    <section>
      <h2 className="text-lg font-semibold mb-4 text-gray-300">{title}</h2>
      {loading ? (
        viewMode === "table" ? (
          <TableSkeleton rows={skeletonCount} />
        ) : (
          renderSkeletons(skeletonCount)
        )
      ) : viewMode === "table" ? (
        <StockTable data={data} searchQuery={searchQuery} />
      ) : (
        renderCards(data)
      )}
    </section>
  );

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-gray-100">
      <Header
        tab={tab}
        setTab={setTab}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
      />

      {/* Market Index Banner */}
      {tab === "overview" && <MarketIndexBanner />}

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {tab === "overview" && (
          <div className="space-y-8">
            {/* View mode toggle */}
            <div className="flex items-center justify-end gap-1">
              <button
                onClick={() => setViewMode("table")}
                className={`px-3 py-1.5 text-xs font-medium rounded-l transition-all border ${
                  viewMode === "table"
                    ? "bg-slate-700/40 text-white border-slate-600/50"
                    : "text-gray-400 hover:text-gray-200 bg-transparent border-gray-700/50 hover:bg-gray-800/50"
                }`}
              >
                Table
              </button>
              <button
                onClick={() => setViewMode("cards")}
                className={`px-3 py-1.5 text-xs font-medium rounded-r transition-all border ${
                  viewMode === "cards"
                    ? "bg-slate-700/40 text-white border-slate-600/50"
                    : "text-gray-400 hover:text-gray-200 bg-transparent border-gray-700/50 hover:bg-gray-800/50"
                }`}
              >
                Cards
              </button>
            </div>

            {/* US Equities */}
            {renderSection("US Equities", filteredUs, 6)}

            {/* Cryptocurrency */}
            {renderSection("Cryptocurrency", filteredCrypto, 3)}

            {/* China A-Shares */}
            {renderSection("China A-Shares", filteredCn, 6)}

            <BacktestTable />
          </div>
        )}
        {tab === "backtest" && <BacktestTable />}
        {tab === "cn-scanner" && <CNScanner />}
        {tab === "strategies" && <StrategyGallery />}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800/30 py-6 mt-12">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <p className="text-xs text-gray-600">
            FinClaw &middot; Open-source quantitative research platform
          </p>
        </div>
      </footer>
    </div>
  );
}
