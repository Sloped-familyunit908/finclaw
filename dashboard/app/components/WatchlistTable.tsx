"use client";

import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { MarketData } from "@/app/types";
import { searchTickers, findTicker, type TickerInfo } from "@/app/lib/tickers";
import { fmt } from "@/app/lib/utils";

/* ── Constants ── */
const STORAGE_KEY = "finclaw_watchlist";
const DEFAULT_WATCHLIST = ["AAPL", "NVDA", "TSLA", "MSFT", "GOOGL", "AMZN", "BTC", "ETH"];

/* ── Sort config ── */
type SortField = "ticker" | "name" | "price" | "change" | "volume" | "marketCap";
type SortDir = "asc" | "desc";

/* ── Helper: detect market ── */
function getMarketLabel(symbol: string): string {
  if (/\.(SH|SZ)$/i.test(symbol)) return "CN";
  if (["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "DOT", "AVAX", "LINK"].includes(symbol.toUpperCase())) return "Crypto";
  return "US";
}

function isCnSymbol(symbol: string): boolean {
  return /\.(SH|SZ)$/i.test(symbol);
}

/* ── Sortable header ── */
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
      className={`py-2.5 px-3 cursor-pointer select-none hover:text-gray-200 transition-colors text-xs uppercase tracking-wider ${className}`}
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

/* ── Add Ticker Input ── */
function AddTickerInput({ onAdd }: { onAdd: (symbol: string) => void }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<TickerInfo[]>([]);
  const [selectedIdx, setSelectedIdx] = useState(-1);
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (query.trim()) {
      setResults(searchTickers(query, 8));
      setOpen(true);
      setSelectedIdx(-1);
    } else {
      setResults([]);
      setOpen(false);
    }
  }, [query]);

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const handleSelect = (symbol: string) => {
    onAdd(symbol);
    setQuery("");
    setOpen(false);
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!open || results.length === 0) {
      if (e.key === "Enter" && query.trim()) {
        // Allow adding arbitrary tickers
        onAdd(query.trim().toUpperCase());
        setQuery("");
        setOpen(false);
      }
      return;
    }

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setSelectedIdx((prev) => Math.min(prev + 1, results.length - 1));
        break;
      case "ArrowUp":
        e.preventDefault();
        setSelectedIdx((prev) => Math.max(prev - 1, -1));
        break;
      case "Enter":
        e.preventDefault();
        if (selectedIdx >= 0 && selectedIdx < results.length) {
          handleSelect(results[selectedIdx].symbol);
        } else if (results.length > 0) {
          handleSelect(results[0].symbol);
        }
        break;
      case "Escape":
        setOpen(false);
        break;
    }
  };

  return (
    <div ref={containerRef} className="relative">
      <div className="flex items-center gap-2">
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => query.trim() && setOpen(true)}
          placeholder="Add ticker..."
          className="w-40 px-3 py-1.5 text-xs bg-gray-900/60 border border-gray-700/50 rounded text-gray-300 placeholder-gray-600 focus:outline-none focus:border-slate-500/60 font-mono"
        />
      </div>

      {open && results.length > 0 && (
        <div className="absolute top-full left-0 mt-1 w-72 bg-[#13131a] border border-gray-700/60 rounded shadow-xl z-50 max-h-64 overflow-y-auto">
          {results.map((t, i) => (
            <button
              key={t.symbol}
              className={`w-full text-left px-3 py-2 text-xs flex items-center justify-between hover:bg-gray-800/60 transition-colors ${
                i === selectedIdx ? "bg-gray-800/60" : ""
              }`}
              onClick={() => handleSelect(t.symbol)}
              onMouseEnter={() => setSelectedIdx(i)}
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className="font-mono font-semibold text-gray-200 shrink-0">
                  {t.symbol}
                </span>
                <span className="text-gray-500 truncate">
                  {t.nameCn || t.name}
                </span>
              </div>
              <span className="text-[10px] text-gray-600 shrink-0 ml-2">
                {t.market}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════
   WATCHLIST TABLE COMPONENT
   ════════════════════════════════════════════════════════════════ */
export default function WatchlistTable() {
  const router = useRouter();
  const [watchlist, setWatchlist] = useState<string[]>([]);
  const [priceData, setPriceData] = useState<Map<string, MarketData>>(new Map());
  const [loading, setLoading] = useState(true);
  const [sortField, setSortField] = useState<SortField>("change");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  // Load watchlist from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setWatchlist(parsed);
          return;
        }
      }
    } catch {
      // ignore
    }
    setWatchlist(DEFAULT_WATCHLIST);
  }, []);

  // Persist watchlist
  const persistWatchlist = useCallback((list: string[]) => {
    setWatchlist(list);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
    } catch {
      // ignore
    }
  }, []);

  // Fetch prices for all watchlist items
  useEffect(() => {
    if (watchlist.length === 0) return;

    let cancelled = false;

    async function fetchPrices() {
      setLoading(true);

      // Group by market
      const us: string[] = [];
      const cn: string[] = [];
      const crypto: string[] = [];

      for (const sym of watchlist) {
        const mkt = getMarketLabel(sym);
        if (mkt === "CN") cn.push(sym);
        else if (mkt === "Crypto") crypto.push(sym);
        else us.push(sym);
      }

      const fetchers = [
        us.length > 0
          ? fetch("/api/prices?market=us").then((r) => r.json()).catch(() => [])
          : Promise.resolve([]),
        cn.length > 0
          ? fetch("/api/prices?market=cn").then((r) => r.json()).catch(() => [])
          : Promise.resolve([]),
        crypto.length > 0
          ? fetch("/api/prices?market=crypto").then((r) => r.json()).catch(() => [])
          : Promise.resolve([]),
      ];

      const [usData, cnData, cryptoData] = await Promise.all(fetchers);

      if (cancelled) return;

      const map = new Map<string, MarketData>();
      const allData = [...usData, ...cnData, ...cryptoData];
      for (const d of allData) {
        if (d && d.asset) {
          map.set(d.asset, d);
        }
      }

      setPriceData(map);
      setLoading(false);
    }

    fetchPrices();
    const interval = setInterval(fetchPrices, 60_000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [watchlist]);

  // Build rows
  const rows = useMemo(() => {
    return watchlist.map((symbol) => {
      const data = priceData.get(symbol);
      const ticker = findTicker(symbol);
      return {
        symbol,
        name: data?.nameCn || ticker?.nameCn || ticker?.name || symbol,
        price: data?.price ?? 0,
        change: data?.change24h ?? 0,
        volume: data?.volume24h ?? null,
        marketCap: data?.marketCap ?? null,
        market: data?.market || getMarketLabel(symbol),
        isCn: isCnSymbol(symbol),
      };
    });
  }, [watchlist, priceData]);

  // Sort
  const sortedRows = useMemo(() => {
    return [...rows].sort((a, b) => {
      let va: number | string;
      let vb: number | string;

      switch (sortField) {
        case "ticker":
          va = a.symbol;
          vb = b.symbol;
          return sortDir === "asc"
            ? va.localeCompare(vb)
            : vb.localeCompare(va);
        case "name":
          va = a.name;
          vb = b.name;
          return sortDir === "asc"
            ? va.localeCompare(vb)
            : vb.localeCompare(va);
        case "price":
          va = a.price;
          vb = b.price;
          break;
        case "change":
          va = a.change;
          vb = b.change;
          break;
        case "volume":
          va = a.volume ?? 0;
          vb = b.volume ?? 0;
          break;
        case "marketCap":
          va = a.marketCap ?? 0;
          vb = b.marketCap ?? 0;
          break;
        default:
          return 0;
      }

      return sortDir === "asc" ? (va as number) - (vb as number) : (vb as number) - (va as number);
    });
  }, [rows, sortField, sortDir]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("desc");
    }
  };

  const handleAdd = (symbol: string) => {
    if (watchlist.some((s) => s.toLowerCase() === symbol.toLowerCase())) return;
    persistWatchlist([...watchlist, symbol]);
  };

  const handleRemove = (symbol: string) => {
    persistWatchlist(watchlist.filter((s) => s !== symbol));
  };

  const handleRowClick = (symbol: string) => {
    router.push(`/stock/${encodeURIComponent(symbol)}`);
  };

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
          Watchlist
        </h2>
        <AddTickerInput onAdd={handleAdd} />
      </div>

      <div className="overflow-x-auto rounded border border-gray-800/60">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-900/50 text-gray-400">
              <SortHeader label="Ticker" field="ticker" currentField={sortField} currentDir={sortDir} onSort={handleSort} className="text-left px-4" />
              <SortHeader label="Name" field="name" currentField={sortField} currentDir={sortDir} onSort={handleSort} className="text-left hidden lg:table-cell" />
              <SortHeader label="Last" field="price" currentField={sortField} currentDir={sortDir} onSort={handleSort} className="text-right" />
              <SortHeader label="Chg%" field="change" currentField={sortField} currentDir={sortDir} onSort={handleSort} className="text-right" />
              <SortHeader label="Volume" field="volume" currentField={sortField} currentDir={sortDir} onSort={handleSort} className="text-right hidden sm:table-cell" />
              <SortHeader label="Mkt Cap" field="marketCap" currentField={sortField} currentDir={sortDir} onSort={handleSort} className="text-right hidden md:table-cell" />
              <th className="py-2.5 px-3 text-right text-xs uppercase tracking-wider w-10"></th>
            </tr>
          </thead>
          <tbody>
            {loading && rows.length === 0 ? (
              Array.from({ length: DEFAULT_WATCHLIST.length }).map((_, i) => (
                <tr key={i} className="border-t border-gray-800/30 animate-pulse">
                  <td className="py-2.5 px-4"><div className="h-4 w-16 bg-gray-800 rounded" /></td>
                  <td className="py-2.5 px-3 hidden lg:table-cell"><div className="h-4 w-24 bg-gray-800 rounded" /></td>
                  <td className="py-2.5 px-3 text-right"><div className="h-4 w-16 bg-gray-800 rounded ml-auto" /></td>
                  <td className="py-2.5 px-3 text-right"><div className="h-4 w-14 bg-gray-800 rounded ml-auto" /></td>
                  <td className="py-2.5 px-3 text-right hidden sm:table-cell"><div className="h-4 w-16 bg-gray-800 rounded ml-auto" /></td>
                  <td className="py-2.5 px-3 text-right hidden md:table-cell"><div className="h-4 w-16 bg-gray-800 rounded ml-auto" /></td>
                  <td className="py-2.5 px-3 w-10" />
                </tr>
              ))
            ) : sortedRows.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-gray-600 text-xs">
                  Watchlist is empty. Add a ticker above.
                </td>
              </tr>
            ) : (
              sortedRows.map((row) => {
                const isUp = row.change >= 0;
                const fmtPrice = row.price > 0
                  ? row.isCn ? fmt.cny(row.price) : fmt.usd(row.price)
                  : "--";
                const fmtVol = row.volume
                  ? row.isCn ? fmt.compactCn(row.volume) : fmt.compact(row.volume)
                  : "--";
                const fmtCap = row.marketCap
                  ? row.isCn ? fmt.compactCn(row.marketCap) : fmt.compact(row.marketCap)
                  : "--";

                return (
                  <tr
                    key={row.symbol}
                    className="border-t border-gray-800/30 hover:bg-gray-900/40 transition-colors cursor-pointer"
                    onClick={() => handleRowClick(row.symbol)}
                  >
                    <td className="py-2 px-4">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-semibold text-gray-100 text-xs">
                          {row.symbol}
                        </span>
                        <span className="px-1 py-0.5 text-[9px] rounded bg-gray-800/60 text-gray-500">
                          {row.market}
                        </span>
                      </div>
                    </td>
                    <td className="py-2 px-3 text-gray-400 text-xs truncate max-w-[160px] hidden lg:table-cell">
                      {row.name}
                    </td>
                    <td className="py-2 px-3 text-right font-mono text-gray-200 text-xs">
                      {fmtPrice}
                    </td>
                    <td
                      className={`py-2 px-3 text-right font-mono font-bold text-xs ${
                        isUp ? "text-[#22c55e]" : "text-[#ef4444]"
                      }`}
                    >
                      {row.price > 0
                        ? `${isUp ? "+" : ""}${row.change.toFixed(2)}%`
                        : "--"}
                    </td>
                    <td className="py-2 px-3 text-right font-mono text-gray-400 text-xs hidden sm:table-cell">
                      {fmtVol}
                    </td>
                    <td className="py-2 px-3 text-right font-mono text-gray-400 text-xs hidden md:table-cell">
                      {fmtCap}
                    </td>
                    <td className="py-2 px-3 text-right w-10">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRemove(row.symbol);
                        }}
                        className="text-gray-600 hover:text-red-400 transition-colors text-xs font-mono"
                        title="Remove from watchlist"
                      >
                        X
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
