"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { searchTickers, findTicker, type TickerInfo } from "@/app/lib/tickers";
import { fmt } from "@/app/lib/utils";
import LoadingCard, { LoadingTable } from "@/app/components/LoadingCard";
import CorrelationMatrix from "@/app/components/CorrelationMatrix";
import RiskMetrics from "@/app/components/RiskMetrics";
import { useRef } from "react";

/* ════════════════════════════════════════════════════════════════
   TYPES
   ════════════════════════════════════════════════════════════════ */

interface Position {
  ticker: string;
  shares: number;
  avgCost: number;
  buyDate: string; // ISO date string
}

interface PositionWithPrice extends Position {
  currentPrice: number;
  prevClose: number;
  name: string;
}

const STORAGE_KEY = "finclaw_portfolio";

/* ════════════════════════════════════════════════════════════════
   ADD POSITION MODAL
   ════════════════════════════════════════════════════════════════ */

function AddPositionModal({
  onAdd,
  onClose,
}: {
  onAdd: (p: Position) => void;
  onClose: () => void;
}) {
  const [ticker, setTicker] = useState("");
  const [shares, setShares] = useState("");
  const [avgCost, setAvgCost] = useState("");
  const [buyDate, setBuyDate] = useState(
    new Date().toISOString().split("T")[0]
  );
  const [results, setResults] = useState<TickerInfo[]>([]);
  const [selectedIdx, setSelectedIdx] = useState(-1);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ticker.trim().length >= 1) {
      setResults(searchTickers(ticker, 6));
      setDropdownOpen(true);
      setSelectedIdx(-1);
    } else {
      setResults([]);
      setDropdownOpen(false);
    }
  }, [ticker]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const selectTicker = (symbol: string) => {
    setTicker(symbol);
    setDropdownOpen(false);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const t = ticker.trim().toUpperCase();
    if (!t || !shares || !avgCost) return;
    onAdd({
      ticker: t,
      shares: parseFloat(shares),
      avgCost: parseFloat(avgCost),
      buyDate,
    });
    onClose();
  };

  return (
    <div
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-[100]"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-[#13131a] border border-gray-800/60 rounded-lg p-6 w-full max-w-md animate-fade-in">
        <h3 className="text-sm font-semibold text-gray-300 mb-4">
          Add Position
        </h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Ticker */}
          <div ref={containerRef} className="relative">
            <label className="text-xs text-gray-500 block mb-1">Ticker</label>
            <input
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "ArrowDown" && dropdownOpen) {
                  e.preventDefault();
                  setSelectedIdx((p) => Math.min(p + 1, results.length - 1));
                } else if (e.key === "ArrowUp" && dropdownOpen) {
                  e.preventDefault();
                  setSelectedIdx((p) => Math.max(p - 1, -1));
                } else if (e.key === "Enter" && dropdownOpen && selectedIdx >= 0) {
                  e.preventDefault();
                  selectTicker(results[selectedIdx].symbol);
                }
              }}
              placeholder="AAPL"
              className="w-full px-3 py-2 text-sm bg-gray-900/60 border border-gray-700/50 rounded text-gray-200 placeholder-gray-600 focus:outline-none focus:border-slate-500/60 font-mono"
              required
            />
            {dropdownOpen && results.length > 0 && (
              <div className="absolute top-full left-0 mt-1 w-full bg-[#13131a] border border-gray-700/60 rounded shadow-xl z-50 max-h-48 overflow-y-auto">
                {results.map((t, i) => (
                  <button
                    key={t.symbol}
                    type="button"
                    className={`w-full text-left px-3 py-2 text-xs flex items-center justify-between hover:bg-gray-800/60 transition-colors ${
                      i === selectedIdx ? "bg-gray-800/60" : ""
                    }`}
                    onClick={() => selectTicker(t.symbol)}
                  >
                    <span className="font-mono text-gray-200">{t.symbol}</span>
                    <span className="text-gray-500 truncate ml-2">
                      {t.nameCn || t.name}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Shares & Avg Cost */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Shares</label>
              <input
                type="number"
                value={shares}
                onChange={(e) => setShares(e.target.value)}
                placeholder="100"
                step="any"
                className="w-full px-3 py-2 text-sm bg-gray-900/60 border border-gray-700/50 rounded text-gray-200 placeholder-gray-600 focus:outline-none focus:border-slate-500/60 font-mono"
                required
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">
                Avg Cost ($)
              </label>
              <input
                type="number"
                value={avgCost}
                onChange={(e) => setAvgCost(e.target.value)}
                placeholder="150.00"
                step="any"
                className="w-full px-3 py-2 text-sm bg-gray-900/60 border border-gray-700/50 rounded text-gray-200 placeholder-gray-600 focus:outline-none focus:border-slate-500/60 font-mono"
                required
              />
            </div>
          </div>

          {/* Buy Date */}
          <div>
            <label className="text-xs text-gray-500 block mb-1">Buy Date</label>
            <input
              type="date"
              value={buyDate}
              onChange={(e) => setBuyDate(e.target.value)}
              className="w-full px-3 py-2 text-sm bg-gray-900/60 border border-gray-700/50 rounded text-gray-200 focus:outline-none focus:border-slate-500/60 font-mono"
            />
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs text-gray-400 hover:text-gray-200 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-xs bg-slate-700/60 border border-slate-600/50 rounded text-white hover:bg-slate-700/80 transition-colors"
            >
              Add Position
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════
   PORTFOLIO PAGE
   ════════════════════════════════════════════════════════════════ */

export default function PortfolioPage() {
  const router = useRouter();
  const [positions, setPositions] = useState<Position[]>([]);
  const [prices, setPrices] = useState<
    Map<string, { price: number; prevClose: number; name: string }>
  >(new Map());
  const [loading, setLoading] = useState(true);
  const [pricesLoading, setPricesLoading] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);

  // Load positions from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          setPositions(parsed);
        }
      }
    } catch {
      // ignore
    }
    setLoading(false);
  }, []);

  // Persist positions
  const persist = useCallback((list: Position[]) => {
    setPositions(list);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
    } catch {
      // ignore
    }
  }, []);

  // Fetch prices for all positions
  useEffect(() => {
    if (positions.length === 0) {
      setPrices(new Map());
      return;
    }

    let cancelled = false;

    async function fetchPrices() {
      setPricesLoading(true);
      try {
        const symbols = positions.map((p) => p.ticker);
        const resp = await fetch(
          `/api/prices?symbols=${encodeURIComponent(symbols.join(","))}`
        );
        const data = await resp.json();

        if (cancelled) return;

        const map = new Map<string, { price: number; prevClose: number; name: string }>();
        if (Array.isArray(data)) {
          for (const d of data) {
            if (d && d.asset) {
              const tickerInfo = findTicker(d.asset);
              const prevClose = d.change24h !== undefined && d.price > 0
                ? d.price / (1 + d.change24h / 100)
                : d.price;
              map.set(d.asset, {
                price: d.price ?? 0,
                prevClose,
                name: d.nameCn || tickerInfo?.nameCn || tickerInfo?.name || d.asset,
              });
            }
          }
        }
        setPrices(map);
      } catch {
        // ignore
      } finally {
        if (!cancelled) setPricesLoading(false);
      }
    }

    fetchPrices();
    const interval = setInterval(fetchPrices, 60_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [positions]);

  // Build enriched rows
  const rows: PositionWithPrice[] = useMemo(() => {
    return positions.map((p) => {
      const priceData = prices.get(p.ticker);
      return {
        ...p,
        currentPrice: priceData?.price ?? 0,
        prevClose: priceData?.prevClose ?? 0,
        name: priceData?.name || findTicker(p.ticker)?.name || p.ticker,
      };
    });
  }, [positions, prices]);

  // Portfolio summary
  const summary = useMemo(() => {
    let totalValue = 0;
    let totalCost = 0;
    let todayPnL = 0;

    for (const r of rows) {
      const currentVal = r.currentPrice * r.shares;
      const costVal = r.avgCost * r.shares;
      const prevVal = r.prevClose * r.shares;

      totalValue += currentVal;
      totalCost += costVal;
      if (r.prevClose > 0 && r.currentPrice > 0) {
        todayPnL += currentVal - prevVal;
      }
    }

    return {
      totalValue,
      totalCost,
      totalPnL: totalValue - totalCost,
      totalPnLPct: totalCost > 0 ? ((totalValue - totalCost) / totalCost) * 100 : 0,
      todayPnL,
      todayPnLPct: totalValue > 0 ? (todayPnL / (totalValue - todayPnL)) * 100 : 0,
    };
  }, [rows]);

  const handleAdd = (p: Position) => {
    // If ticker already exists, merge
    const existing = positions.findIndex(
      (pos) => pos.ticker.toUpperCase() === p.ticker.toUpperCase()
    );
    if (existing >= 0) {
      const old = positions[existing];
      const totalShares = old.shares + p.shares;
      const newAvgCost =
        (old.shares * old.avgCost + p.shares * p.avgCost) / totalShares;
      const updated = [...positions];
      updated[existing] = { ...old, shares: totalShares, avgCost: newAvgCost };
      persist(updated);
    } else {
      persist([...positions, p]);
    }
  };

  const handleRemove = (ticker: string) => {
    persist(positions.filter((p) => p.ticker !== ticker));
  };

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800/50 bg-[#0a0a0f]/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="text-xl font-bold text-white tracking-tight hover:opacity-80 transition-opacity"
            >
              FinClaw
            </Link>
            <span className="text-gray-700">|</span>
            <h1 className="text-sm font-semibold text-gray-300">
              Portfolio Manager
            </h1>
          </div>
          <Link
            href="/"
            className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
          >
            Back to Dashboard
          </Link>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* Loading */}
        {loading && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <LoadingCard key={i} rows={2} />
              ))}
            </div>
            <LoadingTable columns={8} rows={4} />
          </div>
        )}

        {!loading && (
          <>
            {/* Summary bar */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="rounded border border-gray-800/60 bg-[#13131a] p-4">
                <p className="text-xs text-gray-500 mb-1">Total Value</p>
                <p className="text-xl font-mono font-bold text-white">
                  {summary.totalValue > 0
                    ? fmt.usd(summary.totalValue)
                    : "$0.00"}
                </p>
              </div>
              <div className="rounded border border-gray-800/60 bg-[#13131a] p-4">
                <p className="text-xs text-gray-500 mb-1">Today P&L</p>
                <p
                  className={`text-xl font-mono font-bold ${
                    summary.todayPnL >= 0 ? "text-[#22c55e]" : "text-[#ef4444]"
                  }`}
                >
                  {summary.todayPnL >= 0 ? "+" : ""}
                  {fmt.usd(summary.todayPnL)}
                </p>
                <p
                  className={`text-xs font-mono ${
                    summary.todayPnLPct >= 0 ? "text-[#22c55e]" : "text-[#ef4444]"
                  }`}
                >
                  {summary.todayPnLPct >= 0 ? "+" : ""}
                  {summary.todayPnLPct.toFixed(2)}%
                </p>
              </div>
              <div className="rounded border border-gray-800/60 bg-[#13131a] p-4">
                <p className="text-xs text-gray-500 mb-1">Total P&L</p>
                <p
                  className={`text-xl font-mono font-bold ${
                    summary.totalPnL >= 0 ? "text-[#22c55e]" : "text-[#ef4444]"
                  }`}
                >
                  {summary.totalPnL >= 0 ? "+" : ""}
                  {fmt.usd(summary.totalPnL)}
                </p>
                <p
                  className={`text-xs font-mono ${
                    summary.totalPnLPct >= 0 ? "text-[#22c55e]" : "text-[#ef4444]"
                  }`}
                >
                  {summary.totalPnLPct >= 0 ? "+" : ""}
                  {summary.totalPnLPct.toFixed(2)}%
                </p>
              </div>
              <div className="rounded border border-gray-800/60 bg-[#13131a] p-4">
                <p className="text-xs text-gray-500 mb-1">Total Cost</p>
                <p className="text-xl font-mono font-bold text-gray-300">
                  {summary.totalCost > 0
                    ? fmt.usd(summary.totalCost)
                    : "$0.00"}
                </p>
                <p className="text-xs text-gray-600">
                  {positions.length} position{positions.length !== 1 ? "s" : ""}
                </p>
              </div>
            </div>

            {/* Add button */}
            <div className="flex justify-end">
              <button
                onClick={() => setShowAddModal(true)}
                className="px-4 py-2 text-xs bg-slate-700/60 border border-slate-600/50 rounded text-white hover:bg-slate-700/80 transition-colors"
              >
                Add Position
              </button>
            </div>

            {/* Empty state */}
            {positions.length === 0 && (
              <div className="rounded border border-gray-800/60 bg-[#13131a] p-12 text-center">
                <p className="text-gray-400 text-sm">No positions yet</p>
                <p className="text-gray-600 text-xs mt-2">
                  Click &quot;Add Position&quot; to start tracking your portfolio
                </p>
              </div>
            )}

            {/* Positions table */}
            {positions.length > 0 && (
              <div className="overflow-x-auto rounded border border-gray-800/60">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-900/50 text-gray-400 text-xs uppercase tracking-wider">
                      <th className="py-2.5 px-4 text-left">Ticker</th>
                      <th className="py-2.5 px-3 text-right">Shares</th>
                      <th className="py-2.5 px-3 text-right">Avg Cost</th>
                      <th className="py-2.5 px-3 text-right">Current</th>
                      <th className="py-2.5 px-3 text-right">P&L</th>
                      <th className="py-2.5 px-3 text-right">P&L%</th>
                      <th className="py-2.5 px-3 text-right hidden sm:table-cell">
                        Weight%
                      </th>
                      <th className="py-2.5 px-3 text-right w-10">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row) => {
                      const pnl = (row.currentPrice - row.avgCost) * row.shares;
                      const pnlPct =
                        row.avgCost > 0
                          ? ((row.currentPrice - row.avgCost) / row.avgCost) * 100
                          : 0;
                      const weight =
                        summary.totalValue > 0
                          ? ((row.currentPrice * row.shares) / summary.totalValue) *
                            100
                          : 0;
                      const isPnlUp = pnl >= 0;
                      const hasPriceData = row.currentPrice > 0;

                      return (
                        <tr
                          key={row.ticker}
                          className="border-t border-gray-800/30 hover:bg-gray-900/40 transition-colors cursor-pointer"
                          onClick={() =>
                            router.push(`/stock/${encodeURIComponent(row.ticker)}`)
                          }
                        >
                          <td className="py-2 px-4">
                            <div>
                              <span className="font-mono font-semibold text-gray-100 text-xs">
                                {row.ticker}
                              </span>
                              <p className="text-[10px] text-gray-500 truncate max-w-[120px]">
                                {row.name}
                              </p>
                            </div>
                          </td>
                          <td className="py-2 px-3 text-right font-mono text-gray-300 text-xs">
                            {row.shares.toLocaleString()}
                          </td>
                          <td className="py-2 px-3 text-right font-mono text-gray-300 text-xs">
                            ${row.avgCost.toFixed(2)}
                          </td>
                          <td className="py-2 px-3 text-right font-mono text-gray-200 text-xs">
                            {hasPriceData ? (
                              `$${row.currentPrice.toFixed(2)}`
                            ) : pricesLoading ? (
                              <span className="inline-block w-12 h-3 bg-gray-800 rounded animate-pulse" />
                            ) : (
                              <span className="text-gray-600">Fetching...</span>
                            )}
                          </td>
                          <td
                            className={`py-2 px-3 text-right font-mono font-bold text-xs ${
                              !hasPriceData
                                ? "text-gray-600"
                                : isPnlUp
                                  ? "text-[#22c55e]"
                                  : "text-[#ef4444]"
                            }`}
                          >
                            {hasPriceData
                              ? `${isPnlUp ? "+" : ""}$${pnl.toFixed(2)}`
                              : "\u2014"}
                          </td>
                          <td
                            className={`py-2 px-3 text-right font-mono font-bold text-xs ${
                              !hasPriceData
                                ? "text-gray-600"
                                : isPnlUp
                                  ? "text-[#22c55e]"
                                  : "text-[#ef4444]"
                            }`}
                          >
                            {hasPriceData
                              ? `${isPnlUp ? "+" : ""}${pnlPct.toFixed(2)}%`
                              : "\u2014"}
                          </td>
                          <td className="py-2 px-3 text-right font-mono text-gray-400 text-xs hidden sm:table-cell">
                            {hasPriceData ? `${weight.toFixed(1)}%` : "\u2014"}
                          </td>
                          <td className="py-2 px-3 text-right w-10">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleRemove(row.ticker);
                              }}
                              className="text-gray-600 hover:text-red-400 transition-colors text-xs font-mono"
                              title="Remove position"
                            >
                              X
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* Correlation Matrix */}
            <CorrelationMatrix tickers={positions.map((p) => p.ticker)} />

            {/* Risk Metrics */}
            <RiskMetrics
              holdings={rows.map((r) => ({
                ticker: r.ticker,
                shares: r.shares,
                currentPrice: r.currentPrice,
              }))}
            />
          </>
        )}
      </main>

      {/* Add Position Modal */}
      {showAddModal && (
        <AddPositionModal
          onAdd={handleAdd}
          onClose={() => setShowAddModal(false)}
        />
      )}

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
