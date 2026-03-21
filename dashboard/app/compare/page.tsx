"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { searchTickers, ALL_TICKERS, type TickerInfo } from "@/app/lib/tickers";
import { fmt } from "@/app/lib/utils";
import type { HistoryBar } from "@/app/api/history/route";

/* ── Types ── */
interface FundamentalsData {
  peRatio: number | null;
  forwardPE: number | null;
  pegRatio: number | null;
  priceToBook: number | null;
  priceToSales: number | null;
  evToEbitda: number | null;
  marketCap: number | null;
  enterpriseValue: number | null;
  totalRevenue: number | null;
  profitMargin: number | null;
  returnOnEquity: number | null;
  revenueGrowth: number | null;
  earningsGrowth: number | null;
  dividendYield: number | null;
  beta: number | null;
  fiftyTwoWeekChange: number | null;
  targetMeanPrice: number | null;
}

interface PriceData {
  price: number;
  change: number;
}

interface StockData {
  price: PriceData | null;
  fundamentals: FundamentalsData | null;
  history: HistoryBar[];
  loading: boolean;
  error: string | null;
}

/* ── Helpers ── */
function isCN(code: string) {
  return /\.(SH|SZ)$/i.test(code);
}

function fmtPrice(price: number, code: string) {
  return isCN(code) ? fmt.cny(price) : fmt.usd(price);
}

function fmtPct(n: number | null): string {
  if (n === null || n === undefined || isNaN(n)) return "\u2014";
  return (n >= 0 ? "+" : "") + (n * 100).toFixed(1) + "%";
}

function fmtPctRaw(n: number): string {
  return (n >= 0 ? "+" : "") + n.toFixed(2) + "%";
}

function fmtCompact(n: number | null): string {
  if (n === null || n === undefined || isNaN(n)) return "\u2014";
  if (Math.abs(n) >= 1e12) return "$" + (n / 1e12).toFixed(2) + "T";
  if (Math.abs(n) >= 1e9) return "$" + (n / 1e9).toFixed(1) + "B";
  if (Math.abs(n) >= 1e6) return "$" + (n / 1e6).toFixed(1) + "M";
  return "$" + n.toLocaleString();
}

function fmtNum(n: number | null): string {
  if (n === null || n === undefined || isNaN(n)) return "\u2014";
  return n.toFixed(2);
}

/* ── Sparkline SVG ── */
function Sparkline({ data, color }: { data: HistoryBar[]; color: string }) {
  if (data.length < 2) return <div className="h-16 flex items-center justify-center text-gray-600 text-xs">No data</div>;

  const closes = data.map((d) => d.close);
  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const range = max - min || 1;
  const w = 240;
  const h = 60;
  const pad = 2;

  const points = closes.map((c, i) => {
    const x = pad + (i / (closes.length - 1)) * (w - 2 * pad);
    const y = pad + (1 - (c - min) / range) * (h - 2 * pad);
    return `${x},${y}`;
  }).join(" ");

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-16" preserveAspectRatio="none">
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

/* ── Ticker Selector ── */
function TickerSelector({
  value,
  onChange,
  label,
}: {
  value: string;
  onChange: (ticker: string) => void;
  label: string;
}) {
  const [query, setQuery] = useState(value);
  const [results, setResults] = useState<TickerInfo[]>([]);
  const [open, setOpen] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(-1);

  useEffect(() => {
    setQuery(value);
  }, [value]);

  useEffect(() => {
    if (query.trim() && query !== value) {
      setResults(searchTickers(query, 8));
      setOpen(true);
      setSelectedIdx(-1);
    } else {
      setResults([]);
      setOpen(false);
    }
  }, [query, value]);

  const select = useCallback((symbol: string) => {
    setQuery(symbol);
    setOpen(false);
    onChange(symbol);
  }, [onChange]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!open || results.length === 0) {
      if (e.key === "Enter" && query.trim()) {
        select(query.trim().toUpperCase());
      }
      return;
    }
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setSelectedIdx((p) => Math.min(p + 1, results.length - 1));
        break;
      case "ArrowUp":
        e.preventDefault();
        setSelectedIdx((p) => Math.max(p - 1, -1));
        break;
      case "Enter":
        e.preventDefault();
        if (selectedIdx >= 0) select(results[selectedIdx].symbol);
        else if (results.length > 0) select(results[0].symbol);
        break;
      case "Escape":
        setOpen(false);
        break;
    }
  };

  return (
    <div className="relative">
      <label className="block text-[10px] text-gray-600 uppercase tracking-wider mb-1">
        {label}
      </label>
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        onFocus={() => { if (query.trim() && query !== value) setOpen(true); }}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        placeholder="Type ticker..."
        className="w-full px-3 py-2 text-sm bg-gray-900/60 border border-gray-700/50 rounded text-gray-200 placeholder-gray-600 focus:outline-none focus:border-slate-500/60 font-mono"
      />
      {open && results.length > 0 && (
        <div className="absolute top-full left-0 mt-1 w-full bg-[#13131a] border border-gray-700/60 rounded shadow-xl z-[60] max-h-60 overflow-y-auto">
          {results.map((t, i) => (
            <button
              key={t.symbol}
              className={`w-full text-left px-3 py-2 text-xs flex items-center justify-between hover:bg-gray-800/60 transition-colors border-b border-gray-800/30 last:border-0 ${
                i === selectedIdx ? "bg-gray-800/60" : ""
              }`}
              onMouseDown={() => select(t.symbol)}
              onMouseEnter={() => setSelectedIdx(i)}
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className="font-mono font-semibold text-gray-200 shrink-0">{t.symbol}</span>
                <span className="text-gray-500 truncate">
                  {t.nameCn ? `${t.nameCn} (${t.name})` : t.name}
                </span>
              </div>
              <span className={`text-[10px] shrink-0 ml-2 px-1.5 py-0.5 rounded ${
                t.market === "US" ? "text-blue-400 bg-blue-950/40"
                  : t.market === "CN" ? "text-yellow-400 bg-yellow-950/40"
                    : "text-purple-400 bg-purple-950/40"
              }`}>{t.market}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Metric Row ── */
type MetricDir = "higher" | "lower";

interface MetricDef {
  label: string;
  key: string;
  format: (v: number | null) => string;
  direction: MetricDir;
  note?: string;
}

function determineWinner(
  a: number | null,
  b: number | null,
  direction: MetricDir,
): "a" | "b" | null {
  if (a === null || b === null || isNaN(a) || isNaN(b)) return null;
  if (a === b) return null;
  if (direction === "higher") return a > b ? "a" : "b";
  return a < b ? "a" : "b";
}

/* ── Data fetching hook ── */
function useStockData(code: string): StockData {
  const [price, setPrice] = useState<PriceData | null>(null);
  const [fundamentals, setFundamentals] = useState<FundamentalsData | null>(null);
  const [history, setHistory] = useState<HistoryBar[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!code) {
      setPrice(null);
      setFundamentals(null);
      setHistory([]);
      return;
    }

    setLoading(true);
    setError(null);

    const cn = isCN(code);
    const market = cn ? "cn" : /^(BTC|ETH|SOL)$/i.test(code) ? "crypto" : "us";

    Promise.all([
      // Fetch price
      fetch(`/api/prices?market=${market}`)
        .then((r) => r.json())
        .then((data: Array<{ asset: string; price: number; change24h: number }>) => {
          const match = data.find(
            (d) => d.asset.toLowerCase() === code.toLowerCase(),
          );
          if (match) {
            setPrice({ price: match.price, change: match.change24h });
          } else {
            // If not in watchlist, fetch history and derive price
            setPrice(null);
          }
        })
        .catch(() => setPrice(null)),

      // Fetch fundamentals
      fetch(`/api/fundamentals?code=${encodeURIComponent(code)}`)
        .then((r) => r.json())
        .then((data) => {
          if (data && typeof data === "object" && data.peRatio !== undefined) {
            setFundamentals(data);
          }
        })
        .catch(() => setFundamentals(null)),

      // Fetch 1-week history for sparkline
      fetch(`/api/history?code=${encodeURIComponent(code)}&range=1w`)
        .then((r) => r.json())
        .then((data) => {
          if (Array.isArray(data) && data.length > 0) {
            setHistory(data);
            // derive price from history if prices API didn't have it
            setPrice((prev) => {
              if (prev) return prev;
              const last = data[data.length - 1];
              const prev2 = data.length > 1 ? data[data.length - 2] : null;
              const prevClose = prev2?.close ?? last.open;
              const change = prevClose > 0 ? ((last.close - prevClose) / prevClose) * 100 : 0;
              return { price: last.close, change };
            });
          }
        })
        .catch(() => setHistory([])),
    ]).finally(() => setLoading(false));
  }, [code]);

  return { price, fundamentals, history, loading, error };
}

/* ════════════════════════════════════════════════════════════════
   COMPARE PAGE
   ════════════════════════════════════════════════════════════════ */
import { Suspense } from "react";

function CompareContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const tickerA = searchParams.get("a") ?? "";
  const tickerB = searchParams.get("b") ?? "";

  const dataA = useStockData(tickerA);
  const dataB = useStockData(tickerB);

  const setTickers = useCallback(
    (a: string, b: string) => {
      const params = new URLSearchParams();
      if (a) params.set("a", a);
      if (b) params.set("b", b);
      router.replace(`/compare?${params.toString()}`);
    },
    [router],
  );

  /* ── Metrics definition ── */
  const metrics: MetricDef[] = useMemo(() => {
    return [
      { label: "Price", key: "price", format: (v: number | null) => v !== null ? (isCN(tickerA || tickerB) ? fmt.cny(v) : fmt.usd(v)) : "\u2014", direction: "higher" as MetricDir },
      { label: "Change %", key: "change", format: (v: number | null) => v !== null ? fmtPctRaw(v) : "\u2014", direction: "higher" as MetricDir },
      { label: "PE (TTM)", key: "peRatio", format: fmtNum, direction: "lower" as MetricDir },
      { label: "Forward PE", key: "forwardPE", format: fmtNum, direction: "lower" as MetricDir },
      { label: "ROE", key: "returnOnEquity", format: fmtPct, direction: "higher" as MetricDir },
      { label: "Rev Growth", key: "revenueGrowth", format: fmtPct, direction: "higher" as MetricDir },
      { label: "Profit Margin", key: "profitMargin", format: fmtPct, direction: "higher" as MetricDir },
      { label: "Beta", key: "beta", format: fmtNum, direction: "lower" as MetricDir, note: "lower = safer" },
      { label: "Market Cap", key: "marketCap", format: fmtCompact, direction: "higher" as MetricDir },
      { label: "Div Yield", key: "dividendYield", format: fmtPct, direction: "higher" as MetricDir },
    ];
  }, [tickerA, tickerB]);

  const getVal = useCallback(
    (side: "a" | "b", key: string): number | null => {
      const data = side === "a" ? dataA : dataB;
      if (key === "price") return data.price?.price ?? null;
      if (key === "change") return data.price?.change ?? null;
      return (data.fundamentals as unknown as Record<string, unknown>)?.[key] as number | null ?? null;
    },
    [dataA, dataB],
  );

  const hasBoth = tickerA && tickerB;
  const loading = dataA.loading || dataB.loading;

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800/40 bg-[#0a0a0f]/90 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-4">
          <Link
            href="/"
            className="text-gray-400 hover:text-white transition-colors text-sm"
          >
            Back to Dashboard
          </Link>
          <div className="w-px h-5 bg-gray-700" />
          <h1 className="text-xl font-bold text-white">Compare Stocks</h1>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* Ticker Selectors */}
        <section className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <TickerSelector
            value={tickerA}
            onChange={(t) => setTickers(t, tickerB)}
            label="Ticker A"
          />
          <TickerSelector
            value={tickerB}
            onChange={(t) => setTickers(tickerA, t)}
            label="Ticker B"
          />
        </section>

        {/* Prompt if only one ticker */}
        {tickerA && !tickerB && (
          <div className="rounded border border-gray-800/60 bg-[#13131a] p-6 text-center">
            <p className="text-gray-500 text-sm">Select a second ticker to compare with <span className="font-mono text-gray-300">{tickerA}</span></p>
          </div>
        )}
        {!tickerA && tickerB && (
          <div className="rounded border border-gray-800/60 bg-[#13131a] p-6 text-center">
            <p className="text-gray-500 text-sm">Select a first ticker to compare with <span className="font-mono text-gray-300">{tickerB}</span></p>
          </div>
        )}
        {!tickerA && !tickerB && (
          <div className="rounded border border-gray-800/60 bg-[#13131a] p-6 text-center">
            <p className="text-gray-500 text-sm">Select two tickers above to compare</p>
          </div>
        )}

        {/* Loading */}
        {loading && (tickerA || tickerB) && (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin w-6 h-6 border-2 border-slate-500 border-t-transparent rounded-full" />
            <span className="ml-3 text-gray-400 text-sm">Loading data...</span>
          </div>
        )}

        {/* Side-by-side price cards */}
        {(tickerA || tickerB) && !loading && (
          <section className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Card A */}
            {tickerA && (
              <div className="rounded border border-gray-800/60 bg-[#13131a] p-5">
                <div className="flex items-center justify-between mb-3">
                  <span className="font-mono font-semibold text-gray-200">{tickerA}</span>
                  <Link href={`/stock/${encodeURIComponent(tickerA)}`} className="text-[10px] text-gray-600 hover:text-gray-400">
                    Detail
                  </Link>
                </div>
                {dataA.price ? (
                  <>
                    <p className="text-2xl font-mono font-bold text-white">
                      {fmtPrice(dataA.price.price, tickerA)}
                    </p>
                    <span className={`text-sm font-mono font-bold ${dataA.price.change >= 0 ? "text-[#22c55e]" : "text-[#ef4444]"}`}>
                      {fmtPctRaw(dataA.price.change)}
                    </span>
                  </>
                ) : (
                  <p className="text-gray-600 text-sm">No price data</p>
                )}
                <div className="mt-3">
                  <Sparkline
                    data={dataA.history}
                    color={dataA.price && dataA.price.change >= 0 ? "#22c55e" : "#ef4444"}
                  />
                </div>
              </div>
            )}

            {/* Card B */}
            {tickerB && (
              <div className="rounded border border-gray-800/60 bg-[#13131a] p-5">
                <div className="flex items-center justify-between mb-3">
                  <span className="font-mono font-semibold text-gray-200">{tickerB}</span>
                  <Link href={`/stock/${encodeURIComponent(tickerB)}`} className="text-[10px] text-gray-600 hover:text-gray-400">
                    Detail
                  </Link>
                </div>
                {dataB.price ? (
                  <>
                    <p className="text-2xl font-mono font-bold text-white">
                      {fmtPrice(dataB.price.price, tickerB)}
                    </p>
                    <span className={`text-sm font-mono font-bold ${dataB.price.change >= 0 ? "text-[#22c55e]" : "text-[#ef4444]"}`}>
                      {fmtPctRaw(dataB.price.change)}
                    </span>
                  </>
                ) : (
                  <p className="text-gray-600 text-sm">No price data</p>
                )}
                <div className="mt-3">
                  <Sparkline
                    data={dataB.history}
                    color={dataB.price && dataB.price.change >= 0 ? "#22c55e" : "#ef4444"}
                  />
                </div>
              </div>
            )}
          </section>
        )}

        {/* Metrics Comparison Table */}
        {hasBoth && !loading && (
          <section className="rounded border border-gray-800/60 bg-[#13131a] p-5">
            <h2 className="text-sm font-semibold text-gray-400 mb-4">
              Metrics Comparison
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-800/40">
                    <th className="text-left py-2 pr-4 text-xs text-gray-500 font-medium">Metric</th>
                    <th className="text-right py-2 px-4 text-xs text-gray-500 font-medium font-mono">{tickerA}</th>
                    <th className="text-right py-2 px-4 text-xs text-gray-500 font-medium font-mono">{tickerB}</th>
                    <th className="text-right py-2 pl-4 text-xs text-gray-500 font-medium">Winner</th>
                  </tr>
                </thead>
                <tbody>
                  {metrics.map((m) => {
                    const valA = getVal("a", m.key);
                    const valB = getVal("b", m.key);
                    const winner = determineWinner(valA, valB, m.direction);

                    return (
                      <tr key={m.key} className="border-b border-gray-800/20">
                        <td className="py-2 pr-4 text-gray-400 text-xs">{m.label}</td>
                        <td className={`py-2 px-4 text-right font-mono text-xs ${
                          winner === "a" ? "text-[#22c55e] font-bold" : "text-gray-300"
                        }`}>
                          {m.format(valA)}
                        </td>
                        <td className={`py-2 px-4 text-right font-mono text-xs ${
                          winner === "b" ? "text-[#22c55e] font-bold" : "text-gray-300"
                        }`}>
                          {m.format(valB)}
                        </td>
                        <td className="py-2 pl-4 text-right text-xs">
                          {winner ? (
                            <span className="text-[#22c55e] font-mono">
                              {winner === "a" ? tickerA : tickerB}
                              {m.note ? ` (${m.note})` : ""}
                            </span>
                          ) : (
                            <span className="text-gray-700">\u2014</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <p className="text-[9px] text-gray-700 mt-3 pt-2 border-t border-gray-800/30">
              Data from Yahoo Finance. Delayed. Not investment advice.
            </p>
          </section>
        )}
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

export default function ComparePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
          <div className="animate-spin w-8 h-8 border-2 border-slate-500 border-t-transparent rounded-full" />
        </div>
      }
    >
      <CompareContent />
    </Suspense>
  );
}
