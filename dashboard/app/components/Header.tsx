"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { searchTickers, type TickerInfo } from "@/app/lib/tickers";
import DataFreshnessIndicator from "@/app/components/DataFreshnessIndicator";
import { AlertsBadge } from "@/app/components/PriceAlerts";
import { Input } from "@/app/components/ui/input";
import { Button } from "@/app/components/ui/button";
import { Badge } from "@/app/components/ui/badge";

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
      <Input
        ref={inputRef}
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        onFocus={() => query.trim() && setOpen(true)}
        placeholder="Search ticker..."
        className="w-48 h-8"
      />

      {open && results.length > 0 && (
        <div className="absolute top-full right-0 mt-1 w-80 bg-[#13131a] border border-gray-700/60 rounded-md shadow-xl z-[60] max-h-80 overflow-y-auto">
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
              <Badge
                variant={
                  t.market === "US"
                    ? "info"
                    : t.market === "CN"
                      ? "warning"
                      : "purple"
                }
                className="text-[10px] shrink-0 ml-2"
              >
                {t.market}
              </Badge>
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

  const navItems = [
    { href: "/", label: "Dashboard" },
    { href: "/evolution", label: "Evolution" },
    { href: "/portfolio", label: "Portfolio" },
    { href: "/screener", label: "Screener" },
    { href: "/compare", label: "Compare" },
    { href: "/backtest", label: "Backtest" },
  ];

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
        {navItems.map((item) => (
          <Button
            key={item.href}
            variant="ghost"
            size="sm"
            asChild
          >
            <Link href={item.href} className="whitespace-nowrap">
              {item.label}
            </Link>
          </Button>
        ))}
      </div>
    </header>
  );
}
