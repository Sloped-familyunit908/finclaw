"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { searchTickers, type TickerInfo } from "@/app/lib/tickers";
import DataFreshnessIndicator from "@/app/components/DataFreshnessIndicator";
import { AlertsBadge } from "@/app/components/PriceAlerts";

/* ── Search Component ── */
function SearchBox() {
  const router = useRouter();
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

  const navigateTo = (symbol: string) => {
    router.push(`/stock/${encodeURIComponent(symbol)}`);
    setQuery("");
    setOpen(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!open || results.length === 0) {
      if (e.key === "Enter" && query.trim()) {
        navigateTo(query.trim().toUpperCase());
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
          navigateTo(results[selectedIdx].symbol);
        } else if (results.length > 0) {
          navigateTo(results[0].symbol);
        }
        break;
      case "Escape":
        setOpen(false);
        break;
    }
  };

  return (
    <div ref={containerRef} className="relative hidden md:block">
      <input
        ref={inputRef}
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        onFocus={() => query.trim() && setOpen(true)}
        placeholder="Search ticker..."
        className="w-48 px-3 py-1.5 text-xs bg-gray-900/60 border border-gray-700/50 rounded text-gray-300 placeholder-gray-600 focus:outline-none focus:border-slate-500/60 font-mono"
      />

      {open && results.length > 0 && (
        <div className="absolute top-full right-0 mt-1 w-80 bg-[#13131a] border border-gray-700/60 rounded shadow-xl z-[60] max-h-80 overflow-y-auto">
          {results.map((t, i) => (
            <button
              key={t.symbol}
              className={`w-full text-left px-3 py-2.5 text-xs flex items-center justify-between hover:bg-gray-800/60 transition-colors border-b border-gray-800/30 last:border-0 ${
                i === selectedIdx ? "bg-gray-800/60" : ""
              }`}
              onClick={() => navigateTo(t.symbol)}
              onMouseEnter={() => setSelectedIdx(i)}
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className="font-mono font-semibold text-gray-200 shrink-0">
                  {t.symbol}
                </span>
                <span className="text-gray-500 truncate">
                  {t.nameCn ? `${t.nameCn} (${t.name})` : t.name}
                </span>
              </div>
              <span className={`text-[10px] shrink-0 ml-2 px-1.5 py-0.5 rounded ${
                t.market === "US"
                  ? "text-blue-400 bg-blue-950/40"
                  : t.market === "CN"
                    ? "text-yellow-400 bg-yellow-950/40"
                    : "text-purple-400 bg-purple-950/40"
              }`}>
                {t.market}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Header() {
  const [clock, setClock] = useState("");

  useEffect(() => {
    const tick = () =>
      setClock(new Date().toLocaleTimeString("en-US", { hour12: false }));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <header className="border-b border-gray-800/50 bg-[#0a0a0f]/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">
              FinClaw
            </h1>
            <p className="text-[10px] text-gray-500 tracking-wider uppercase">
              Quantitative Research Platform
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <DataFreshnessIndicator />
          <AlertsBadge />
          <SearchBox />
          <span className="font-mono text-xs text-gray-500">{clock}</span>
        </div>
      </div>
      <div className="max-w-7xl mx-auto px-4 pb-2 flex gap-1 overflow-x-auto scrollbar-hide">
        <Link
          href="/"
          className="px-3 py-2 text-sm font-medium rounded transition-all whitespace-nowrap text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
        >
          Dashboard
        </Link>
        <Link
          href="/evolution"
          className="px-3 py-2 text-sm font-medium rounded transition-all whitespace-nowrap text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
        >
          Evolution
        </Link>
        <Link
          href="/portfolio"
          className="px-3 py-2 text-sm font-medium rounded transition-all whitespace-nowrap text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
        >
          Portfolio
        </Link>
        <Link
          href="/screener"
          className="px-3 py-2 text-sm font-medium rounded transition-all whitespace-nowrap text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
        >
          Screener
        </Link>
        <Link
          href="/compare"
          className="px-3 py-2 text-sm font-medium rounded transition-all whitespace-nowrap text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
        >
          Compare
        </Link>
        <Link
          href="/backtest"
          className="px-3 py-2 text-sm font-medium rounded transition-all whitespace-nowrap text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
        >
          Backtest
        </Link>
      </div>
    </header>
  );
}
