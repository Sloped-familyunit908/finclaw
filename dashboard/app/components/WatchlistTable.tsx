"use client";

import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { MarketData } from "@/app/types";
import { searchTickers, findTicker, type TickerInfo } from "@/app/lib/tickers";
import { fmt } from "@/app/lib/utils";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/app/components/ui/table";
import { Badge } from "@/app/components/ui/badge";
import { Input } from "@/app/components/ui/input";
import { Button } from "@/app/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/app/components/ui/dialog";

/* ── Constants ── */
const STORAGE_KEY = "finclaw_watchlist"; // legacy compat
const MULTI_STORAGE_KEY = "finclaw_watchlists";
const ACTIVE_WATCHLIST_KEY = "finclaw_active_watchlist";
const DEFAULT_WATCHLIST_NAME = "Default";
const DEFAULT_TICKERS = ["AAPL", "NVDA", "TSLA", "MSFT", "GOOGL", "AMZN", "BTC", "ETH"];

/* ── Types ── */
type SortField = "ticker" | "name" | "price" | "change" | "volume" | "marketCap";
type SortDir = "asc" | "desc";

interface WatchlistStore {
  [name: string]: string[];
}

/* ── Helpers ── */
function getMarketLabel(symbol: string): string {
  if (/\.(SH|SZ)$/i.test(symbol)) return "CN";
  if (["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "DOT", "AVAX", "LINK"].includes(symbol.toUpperCase())) return "Crypto";
  return "US";
}

function isCnSymbol(symbol: string): boolean {
  return /\.(SH|SZ)$/i.test(symbol);
}

function getMarketBadgeVariant(market: string): "info" | "warning" | "purple" | "secondary" {
  if (market === "US") return "info";
  if (market === "CN") return "warning";
  if (market === "Crypto") return "purple";
  return "secondary";
}

/* ── Load watchlists (with legacy migration) ── */
function loadWatchlists(): { store: WatchlistStore; active: string } {
  try {
    const multiRaw = localStorage.getItem(MULTI_STORAGE_KEY);
    if (multiRaw) {
      const store = JSON.parse(multiRaw) as WatchlistStore;
      const active = localStorage.getItem(ACTIVE_WATCHLIST_KEY) || DEFAULT_WATCHLIST_NAME;
      if (!store[active]) {
        const first = Object.keys(store)[0] || DEFAULT_WATCHLIST_NAME;
        if (!store[first]) store[first] = DEFAULT_TICKERS;
        return { store, active: first };
      }
      return { store, active };
    }

    const legacyRaw = localStorage.getItem(STORAGE_KEY);
    if (legacyRaw) {
      const parsed = JSON.parse(legacyRaw);
      if (Array.isArray(parsed) && parsed.length > 0) {
        const store: WatchlistStore = { [DEFAULT_WATCHLIST_NAME]: parsed };
        return { store, active: DEFAULT_WATCHLIST_NAME };
      }
    }
  } catch {
    // ignore
  }
  return {
    store: { [DEFAULT_WATCHLIST_NAME]: DEFAULT_TICKERS },
    active: DEFAULT_WATCHLIST_NAME,
  };
}

function saveWatchlists(store: WatchlistStore, active: string) {
  try {
    localStorage.setItem(MULTI_STORAGE_KEY, JSON.stringify(store));
    localStorage.setItem(ACTIVE_WATCHLIST_KEY, active);
    if (store[active]) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(store[active]));
    }
  } catch {
    // ignore
  }
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
    <TableHead
      className={`cursor-pointer select-none hover:text-gray-200 transition-colors ${className}`}
      onClick={() => onSort(field)}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        {isActive && (
          <span className="text-[10px]">{currentDir === "asc" ? "\u25B2" : "\u25BC"}</span>
        )}
      </span>
    </TableHead>
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
      <Input
        ref={inputRef}
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        onFocus={() => query.trim() && setOpen(true)}
        placeholder="Add ticker..."
        className="w-40 h-8"
      />

      {open && results.length > 0 && (
        <div className="absolute top-full left-0 mt-1 w-72 bg-[#13131a] border border-gray-700/60 rounded-md shadow-xl z-50 max-h-64 overflow-y-auto">
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

/* ── New Watchlist Dialog ── */
function NewWatchlistDialog({
  open,
  onAdd,
  onClose,
}: {
  open: boolean;
  onAdd: (name: string) => void;
  onClose: () => void;
}) {
  const [name, setName] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setName("");
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [open]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (trimmed) {
      onAdd(trimmed);
      onClose();
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>New Watchlist</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            ref={inputRef}
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Watchlist name..."
            className="h-9 text-sm"
            required
          />
          <DialogFooter>
            <Button type="button" variant="ghost" size="sm" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" variant="secondary" size="sm">
              Create
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/* ════════════════════════════════════════════════════════════════
   WATCHLIST TABLE COMPONENT
   ════════════════════════════════════════════════════════════════ */
export default function WatchlistTable() {
  const router = useRouter();
  const [watchlistStore, setWatchlistStore] = useState<WatchlistStore>({});
  const [activeWatchlist, setActiveWatchlist] = useState(DEFAULT_WATCHLIST_NAME);
  const [priceData, setPriceData] = useState<Map<string, MarketData>>(new Map());
  const [loading, setLoading] = useState(true);
  const [sortField, setSortField] = useState<SortField>("change");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [showNewWatchlist, setShowNewWatchlist] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const watchlist = watchlistStore[activeWatchlist] || [];
  const watchlistNames = Object.keys(watchlistStore);

  // Load watchlists from localStorage
  useEffect(() => {
    const { store, active } = loadWatchlists();
    setWatchlistStore(store);
    setActiveWatchlist(active);
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  // Persist helper
  const persistStore = useCallback(
    (newStore: WatchlistStore, active?: string) => {
      const act = active ?? activeWatchlist;
      setWatchlistStore(newStore);
      if (active !== undefined) setActiveWatchlist(act);
      saveWatchlists(newStore, act);
    },
    [activeWatchlist]
  );

  // Fetch prices for current watchlist items
  useEffect(() => {
    if (watchlist.length === 0) {
      setLoading(false);
      return;
    }

    let cancelled = false;

    async function fetchPrices() {
      setLoading(true);

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

      const missing = watchlist.filter((sym) => !map.has(sym));
      if (missing.length > 0) {
        try {
          const extra = await fetch(
            `/api/prices?symbols=${encodeURIComponent(missing.join(","))}`
          ).then((r) => r.json()).catch(() => []);
          for (const d of extra) {
            if (d && d.asset) {
              map.set(d.asset, d);
            }
          }
        } catch {
          // ignore
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
    const newStore = {
      ...watchlistStore,
      [activeWatchlist]: [...watchlist, symbol],
    };
    persistStore(newStore);
  };

  const handleRemove = (symbol: string) => {
    const newStore = {
      ...watchlistStore,
      [activeWatchlist]: watchlist.filter((s) => s !== symbol),
    };
    persistStore(newStore);
  };

  const handleNewWatchlist = (name: string) => {
    if (watchlistStore[name]) return;
    const newStore = { ...watchlistStore, [name]: [] };
    persistStore(newStore, name);
  };

  const handleSwitchWatchlist = (name: string) => {
    setActiveWatchlist(name);
    saveWatchlists(watchlistStore, name);
    setShowDropdown(false);
  };

  const handleDeleteWatchlist = (name: string) => {
    if (name === DEFAULT_WATCHLIST_NAME) return;
    if (watchlistNames.length <= 1) return;
    const newStore = { ...watchlistStore };
    delete newStore[name];
    const newActive = name === activeWatchlist
      ? Object.keys(newStore)[0] || DEFAULT_WATCHLIST_NAME
      : activeWatchlist;
    if (!newStore[newActive]) newStore[newActive] = [];
    persistStore(newStore, newActive);
  };

  const handleRowClick = (symbol: string) => {
    router.push(`/stock/${encodeURIComponent(symbol)}`);
  };

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
            Watchlist
          </h2>

          {/* Watchlist selector dropdown */}
          <div ref={dropdownRef} className="relative">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowDropdown(!showDropdown)}
              className="h-7 text-xs gap-1"
            >
              {activeWatchlist}
              <span className="text-[10px] text-gray-500">
                {showDropdown ? "\u25B2" : "\u25BC"}
              </span>
            </Button>

            {showDropdown && (
              <div className="absolute top-full left-0 mt-1 w-48 bg-[#13131a] border border-gray-700/60 rounded-md shadow-xl z-50">
                {watchlistNames.map((name) => (
                  <div
                    key={name}
                    className={`flex items-center justify-between px-3 py-2 text-xs hover:bg-gray-800/60 transition-colors cursor-pointer ${
                      name === activeWatchlist ? "text-white bg-gray-800/40" : "text-gray-400"
                    }`}
                  >
                    <button
                      className="flex-1 text-left"
                      onClick={() => handleSwitchWatchlist(name)}
                    >
                      {name}
                      <span className="text-[10px] text-gray-600 ml-1">
                        ({(watchlistStore[name] || []).length})
                      </span>
                    </button>
                    {name !== DEFAULT_WATCHLIST_NAME && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteWatchlist(name);
                        }}
                        className="text-gray-600 hover:text-red-400 transition-colors ml-2"
                        title="Delete watchlist"
                      >
                        ✕
                      </button>
                    )}
                  </div>
                ))}
                <div className="border-t border-gray-800/40">
                  <button
                    onClick={() => {
                      setShowDropdown(false);
                      setShowNewWatchlist(true);
                    }}
                    className="w-full text-left px-3 py-2 text-xs text-gray-500 hover:text-gray-300 hover:bg-gray-800/60 transition-colors"
                  >
                    + New Watchlist
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        <AddTickerInput onAdd={handleAdd} />
      </div>

      <div className="rounded-lg border border-gray-800/60 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-gray-900/50 hover:bg-gray-900/50">
              <SortHeader label="Ticker" field="ticker" currentField={sortField} currentDir={sortDir} onSort={handleSort} className="text-left px-4" />
              <SortHeader label="Name" field="name" currentField={sortField} currentDir={sortDir} onSort={handleSort} className="text-left hidden lg:table-cell" />
              <SortHeader label="Last" field="price" currentField={sortField} currentDir={sortDir} onSort={handleSort} className="text-right" />
              <SortHeader label="Chg%" field="change" currentField={sortField} currentDir={sortDir} onSort={handleSort} className="text-right" />
              <SortHeader label="Volume" field="volume" currentField={sortField} currentDir={sortDir} onSort={handleSort} className="text-right hidden sm:table-cell" />
              <SortHeader label="Mkt Cap" field="marketCap" currentField={sortField} currentDir={sortDir} onSort={handleSort} className="text-right hidden md:table-cell" />
              <TableHead className="text-right w-10"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading && rows.length === 0 ? (
              Array.from({ length: DEFAULT_TICKERS.length }).map((_, i) => (
                <TableRow key={i} className="animate-pulse">
                  <TableCell className="px-4"><div className="h-4 w-16 bg-gray-800 rounded" /></TableCell>
                  <TableCell className="hidden lg:table-cell"><div className="h-4 w-24 bg-gray-800 rounded" /></TableCell>
                  <TableCell className="text-right"><div className="h-4 w-16 bg-gray-800 rounded ml-auto" /></TableCell>
                  <TableCell className="text-right"><div className="h-4 w-14 bg-gray-800 rounded ml-auto" /></TableCell>
                  <TableCell className="text-right hidden sm:table-cell"><div className="h-4 w-16 bg-gray-800 rounded ml-auto" /></TableCell>
                  <TableCell className="text-right hidden md:table-cell"><div className="h-4 w-16 bg-gray-800 rounded ml-auto" /></TableCell>
                  <TableCell className="w-10" />
                </TableRow>
              ))
            ) : sortedRows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="py-8 text-center text-gray-600 text-xs">
                  Watchlist is empty. Add a ticker above.
                </TableCell>
              </TableRow>
            ) : (
              sortedRows.map((row) => {
                const isUp = row.change >= 0;
                const fmtPrice = row.price > 0
                  ? row.isCn ? fmt.cny(row.price) : fmt.usd(row.price)
                  : "--";
                const fmtVol = row.volume
                  ? row.isCn ? fmt.compactCn(row.volume) : fmt.compact(row.volume)
                  : "N/A";
                const fmtCap = row.marketCap
                  ? row.isCn ? fmt.compactCn(row.marketCap) : fmt.compact(row.marketCap)
                  : "N/A";

                return (
                  <TableRow
                    key={row.symbol}
                    className="cursor-pointer"
                    onClick={() => handleRowClick(row.symbol)}
                  >
                    <TableCell className="px-4">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-semibold text-gray-100 text-xs">
                          {row.symbol}
                        </span>
                        <Badge variant={getMarketBadgeVariant(row.market)} className="text-[9px] px-1 py-0">
                          {row.market}
                        </Badge>
                      </div>
                    </TableCell>
                    <TableCell className="text-gray-400 text-xs truncate max-w-[160px] hidden lg:table-cell">
                      {row.name}
                    </TableCell>
                    <TableCell className="text-right font-mono text-gray-200 text-xs">
                      {fmtPrice}
                    </TableCell>
                    <TableCell
                      className={`text-right font-mono font-bold text-xs ${
                        isUp ? "text-[#22c55e]" : "text-[#ef4444]"
                      }`}
                    >
                      {row.price > 0
                        ? `${isUp ? "+" : ""}${row.change.toFixed(2)}%`
                        : "--"}
                    </TableCell>
                    <TableCell className="text-right font-mono text-gray-400 text-xs hidden sm:table-cell">
                      {fmtVol}
                    </TableCell>
                    <TableCell className="text-right font-mono text-gray-400 text-xs hidden md:table-cell">
                      {fmtCap}
                    </TableCell>
                    <TableCell className="text-right w-10">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRemove(row.symbol);
                        }}
                        className="text-gray-600 hover:text-red-400 transition-colors text-xs font-mono"
                        title="Remove from watchlist"
                      >
                        ✕
                      </button>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

      {/* New Watchlist Dialog */}
      <NewWatchlistDialog
        open={showNewWatchlist}
        onAdd={handleNewWatchlist}
        onClose={() => setShowNewWatchlist(false)}
      />
    </section>
  );
}
