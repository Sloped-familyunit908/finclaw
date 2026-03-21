"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Header from "@/app/components/Header";
import {
  createChart,
  ColorType,
  CrosshairMode,
  LineSeries,
} from "lightweight-charts";
import type { IChartApi } from "lightweight-charts";

/* ════════════════════════════════════════════════════════════════
   TYPES
   ════════════════════════════════════════════════════════════════ */

interface EquityPoint {
  date: string;
  value: number;
}

interface Trade {
  date: string;
  action: "BUY" | "SELL";
  price: number;
  shares: number;
  pnl: number | null;
  pnlPct: number | null;
  reason: string;
}

interface BacktestMetrics {
  totalReturn: number;
  sharpe: number;
  maxDrawdown: number;
  winRate: number;
  totalTrades: number;
  profitFactor: number;
}

interface BacktestResult {
  equityCurve: EquityPoint[];
  metrics: BacktestMetrics;
  trades: Trade[];
}

/* ════════════════════════════════════════════════════════════════
   STRATEGIES CONFIG
   ════════════════════════════════════════════════════════════════ */

interface StrategyDef {
  id: string;
  name: string;
  params: { key: string; label: string; defaultValue: number; suffix?: string }[];
}

const STRATEGIES: StrategyDef[] = [
  {
    id: "rsi",
    name: "RSI Mean Reversion",
    params: [
      { key: "rsiBuy", label: "RSI Buy", defaultValue: 30 },
      { key: "rsiSell", label: "RSI Sell", defaultValue: 70 },
      { key: "stopLoss", label: "Stop Loss", defaultValue: 5, suffix: "%" },
      { key: "takeProfit", label: "Take Profit", defaultValue: 20, suffix: "%" },
    ],
  },
  {
    id: "macd",
    name: "MACD Crossover",
    params: [
      { key: "stopLoss", label: "Stop Loss", defaultValue: 5, suffix: "%" },
      { key: "takeProfit", label: "Take Profit", defaultValue: 20, suffix: "%" },
    ],
  },
  {
    id: "bollinger",
    name: "Bollinger Band Squeeze",
    params: [
      { key: "stopLoss", label: "Stop Loss", defaultValue: 5, suffix: "%" },
      { key: "takeProfit", label: "Take Profit", defaultValue: 20, suffix: "%" },
    ],
  },
  {
    id: "golden_cross",
    name: "Golden Cross (SMA 50/200)",
    params: [
      { key: "stopLoss", label: "Stop Loss", defaultValue: 5, suffix: "%" },
      { key: "takeProfit", label: "Take Profit", defaultValue: 20, suffix: "%" },
    ],
  },
];

/* ════════════════════════════════════════════════════════════════
   EQUITY CURVE CHART
   ════════════════════════════════════════════════════════════════ */

function EquityCurveChart({ data }: { data: EquityPoint[] }) {
  const chartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartRef.current || data.length === 0) return;

    const chart: IChartApi = createChart(chartRef.current, {
      width: chartRef.current.clientWidth,
      height: 320,
      layout: {
        background: { type: ColorType.Solid, color: "#13131a" },
        textColor: "#9ca3af",
      },
      grid: {
        vertLines: { color: "#1e1e2e" },
        horzLines: { color: "#1e1e2e" },
      },
      crosshair: { mode: CrosshairMode.Normal },
      timeScale: { borderColor: "#374151" },
      rightPriceScale: { borderColor: "#374151" },
    });

    const series = chart.addSeries(LineSeries, {
      color: "#5eead4",
      lineWidth: 2,
      title: "Portfolio Value",
    });

    series.setData(
      data.map((d) => ({
        time: d.date,
        value: d.value,
      })),
    );

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (chartRef.current) {
        chart.applyOptions({ width: chartRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [data]);

  return <div ref={chartRef} />;
}

/* ════════════════════════════════════════════════════════════════
   METRIC CARD
   ════════════════════════════════════════════════════════════════ */

function MetricCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div className="bg-[#13131a] border border-gray-800/60 rounded p-4">
      <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">
        {label}
      </div>
      <div
        className={`text-xl font-mono font-semibold ${color ?? "text-gray-200"}`}
      >
        {value}
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════
   FORMAT HELPERS
   ════════════════════════════════════════════════════════════════ */

function fmtPct(n: number): string {
  return (n >= 0 ? "+" : "") + (n * 100).toFixed(2) + "%";
}

function fmtUsd(n: number): string {
  return "$" + n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function returnColor(n: number): string {
  if (n > 0) return "text-green-400";
  if (n < 0) return "text-red-400";
  return "text-gray-400";
}

/* ════════════════════════════════════════════════════════════════
   PAGE
   ════════════════════════════════════════════════════════════════ */

export default function BacktestPage() {
  // Form state
  const [strategyId, setStrategyId] = useState("rsi");
  const [ticker, setTicker] = useState("AAPL");
  const [market, setMarket] = useState("US");
  const [startDate, setStartDate] = useState("2024-01-01");
  const [endDate, setEndDate] = useState("2025-12-31");
  const [capital, setCapital] = useState(100_000);
  const [params, setParams] = useState<Record<string, number>>({});

  // Result state
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Trade log pagination
  const [tradePageSize] = useState(20);
  const [tradePage, setTradePage] = useState(0);

  // Initialize params when strategy changes
  const strategy = STRATEGIES.find((s) => s.id === strategyId) ?? STRATEGIES[0];

  useEffect(() => {
    const defaults: Record<string, number> = {};
    for (const p of strategy.params) {
      defaults[p.key] = p.defaultValue;
    }
    setParams(defaults);
  }, [strategyId]); // eslint-disable-line react-hooks/exhaustive-deps

  const runBacktest = useCallback(async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    setTradePage(0);

    try {
      const resp = await fetch("/api/backtest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          strategy: strategyId,
          ticker: ticker.trim().toUpperCase(),
          market,
          startDate,
          endDate,
          capital,
          params,
        }),
      });

      const data = await resp.json();

      if (!resp.ok) {
        setError(data.error || "Backtest failed");
        return;
      }

      setResult(data);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, [strategyId, ticker, market, startDate, endDate, capital, params]);

  const updateParam = (key: string, value: string) => {
    const num = parseFloat(value);
    if (!isNaN(num)) {
      setParams((prev) => ({ ...prev, [key]: num }));
    }
  };

  // Paginated trades
  const paginatedTrades = result
    ? result.trades.slice(
        tradePage * tradePageSize,
        (tradePage + 1) * tradePageSize,
      )
    : [];
  const totalTradePages = result
    ? Math.ceil(result.trades.length / tradePageSize)
    : 0;

  return (
    <>
      <Header />
      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6 animate-fade-in">
        {/* Title */}
        <div>
          <h2 className="text-lg font-semibold text-gray-200">Backtest Lab</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Run strategy backtests on any market with zero config
          </p>
        </div>

        {/* ── Strategy Configuration ── */}
        <div className="bg-[#13131a] border border-gray-800/60 rounded p-5 space-y-4">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
            Strategy Configuration
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Strategy */}
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                Strategy
              </label>
              <select
                value={strategyId}
                onChange={(e) => setStrategyId(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-gray-900/60 border border-gray-700/50 rounded text-gray-200 focus:outline-none focus:border-slate-500/60 font-mono"
              >
                {STRATEGIES.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Ticker */}
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                Ticker
              </label>
              <input
                type="text"
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                placeholder="AAPL"
                className="w-full px-3 py-2 text-sm bg-gray-900/60 border border-gray-700/50 rounded text-gray-200 placeholder-gray-600 focus:outline-none focus:border-slate-500/60 font-mono"
              />
            </div>

            {/* Market */}
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                Market
              </label>
              <select
                value={market}
                onChange={(e) => setMarket(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-gray-900/60 border border-gray-700/50 rounded text-gray-200 focus:outline-none focus:border-slate-500/60 font-mono"
              >
                <option value="US">US</option>
                <option value="CN">CN (A-shares)</option>
                <option value="Crypto">Crypto</option>
              </select>
            </div>

            {/* Capital */}
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                Capital ($)
              </label>
              <input
                type="number"
                value={capital}
                onChange={(e) => setCapital(parseInt(e.target.value) || 100_000)}
                className="w-full px-3 py-2 text-sm bg-gray-900/60 border border-gray-700/50 rounded text-gray-200 placeholder-gray-600 focus:outline-none focus:border-slate-500/60 font-mono"
              />
            </div>
          </div>

          {/* Date range */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                Start Date
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-gray-900/60 border border-gray-700/50 rounded text-gray-200 focus:outline-none focus:border-slate-500/60 font-mono"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                End Date
              </label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-gray-900/60 border border-gray-700/50 rounded text-gray-200 focus:outline-none focus:border-slate-500/60 font-mono"
              />
            </div>
          </div>

          {/* Strategy parameters */}
          {strategy.params.length > 0 && (
            <div>
              <label className="block text-xs text-gray-500 mb-2">
                Parameters
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                {strategy.params.map((p) => (
                  <div key={p.key}>
                    <label className="block text-[11px] text-gray-600 mb-0.5">
                      {p.label}
                      {p.suffix ? ` (${p.suffix})` : ""}
                    </label>
                    <input
                      type="number"
                      value={params[p.key] ?? p.defaultValue}
                      onChange={(e) => updateParam(p.key, e.target.value)}
                      className="w-full px-2 py-1.5 text-sm bg-gray-900/60 border border-gray-700/50 rounded text-gray-200 focus:outline-none focus:border-slate-500/60 font-mono"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Run button */}
          <div className="pt-2">
            <button
              onClick={runBacktest}
              disabled={loading || !ticker.trim()}
              className="px-6 py-2.5 text-sm font-medium rounded bg-teal-600 text-white hover:bg-teal-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <svg
                    className="animate-spin h-4 w-4"
                    viewBox="0 0 24 24"
                    fill="none"
                  >
                    <circle
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="3"
                      className="opacity-25"
                    />
                    <path
                      d="M4 12a8 8 0 018-8"
                      stroke="currentColor"
                      strokeWidth="3"
                      strokeLinecap="round"
                      className="opacity-75"
                    />
                  </svg>
                  Running backtest...
                </span>
              ) : (
                "Run Backtest"
              )}
            </button>
          </div>
        </div>

        {/* ── Error ── */}
        {error && (
          <div className="bg-red-950/30 border border-red-800/60 rounded p-4 text-sm text-red-300">
            {error}
          </div>
        )}

        {/* ── Results ── */}
        {result && (
          <div className="space-y-6 animate-fade-in">
            {/* Equity Curve */}
            <div className="bg-[#13131a] border border-gray-800/60 rounded p-4 sm:p-5">
              <h3 className="text-sm font-semibold text-gray-400 mb-4">
                Equity Curve
              </h3>
              <EquityCurveChart data={result.equityCurve} />
            </div>

            {/* Performance Summary */}
            <div>
              <h3 className="text-sm font-semibold text-gray-400 mb-3 uppercase tracking-wider">
                Performance Summary
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                <MetricCard
                  label="Total Return"
                  value={fmtPct(result.metrics.totalReturn)}
                  color={returnColor(result.metrics.totalReturn)}
                />
                <MetricCard
                  label="Sharpe Ratio"
                  value={result.metrics.sharpe.toFixed(2)}
                  color={
                    result.metrics.sharpe >= 1
                      ? "text-green-400"
                      : result.metrics.sharpe >= 0
                        ? "text-gray-200"
                        : "text-red-400"
                  }
                />
                <MetricCard
                  label="Max Drawdown"
                  value={fmtPct(result.metrics.maxDrawdown)}
                  color="text-red-400"
                />
                <MetricCard
                  label="Win Rate"
                  value={fmtPct(result.metrics.winRate)}
                  color={
                    result.metrics.winRate > 0.5
                      ? "text-green-400"
                      : "text-gray-200"
                  }
                />
                <MetricCard
                  label="Total Trades"
                  value={result.metrics.totalTrades.toString()}
                />
                <MetricCard
                  label="Profit Factor"
                  value={
                    result.metrics.profitFactor === Infinity
                      ? "N/A"
                      : result.metrics.profitFactor.toFixed(2)
                  }
                  color={
                    result.metrics.profitFactor > 1
                      ? "text-green-400"
                      : "text-gray-200"
                  }
                />
              </div>
            </div>

            {/* Trade Log */}
            <div className="bg-[#13131a] border border-gray-800/60 rounded">
              <div className="px-4 py-3 border-b border-gray-800/40 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-gray-400">
                  Trade Log ({result.trades.length} trades)
                </h3>
                {totalTradePages > 1 && (
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <button
                      onClick={() => setTradePage((p) => Math.max(0, p - 1))}
                      disabled={tradePage === 0}
                      className="px-2 py-1 rounded bg-gray-800/50 hover:bg-gray-700/50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    >
                      Prev
                    </button>
                    <span className="font-mono">
                      {tradePage + 1} / {totalTradePages}
                    </span>
                    <button
                      onClick={() =>
                        setTradePage((p) =>
                          Math.min(totalTradePages - 1, p + 1),
                        )
                      }
                      disabled={tradePage >= totalTradePages - 1}
                      className="px-2 py-1 rounded bg-gray-800/50 hover:bg-gray-700/50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    >
                      Next
                    </button>
                  </div>
                )}
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-900/50 text-gray-500 text-xs uppercase tracking-wider">
                      <th className="text-left py-2.5 px-4">Date</th>
                      <th className="text-left py-2.5 px-3">Action</th>
                      <th className="text-right py-2.5 px-3">Price</th>
                      <th className="text-right py-2.5 px-3">Shares</th>
                      <th className="text-right py-2.5 px-3">P&L</th>
                      <th className="text-left py-2.5 px-3">Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedTrades.map((t, i) => (
                      <tr
                        key={`${t.date}-${t.action}-${i}`}
                        className="border-t border-gray-800/30 hover:bg-gray-900/30"
                      >
                        <td className="py-2 px-4 font-mono text-gray-400">
                          {t.date}
                        </td>
                        <td className="py-2 px-3">
                          <span
                            className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                              t.action === "BUY"
                                ? "bg-green-950/40 text-green-400"
                                : "bg-red-950/40 text-red-400"
                            }`}
                          >
                            {t.action}
                          </span>
                        </td>
                        <td className="py-2 px-3 text-right font-mono text-gray-300">
                          {fmtUsd(t.price)}
                        </td>
                        <td className="py-2 px-3 text-right font-mono text-gray-400">
                          {t.shares}
                        </td>
                        <td
                          className={`py-2 px-3 text-right font-mono ${
                            t.pnl === null
                              ? "text-gray-600"
                              : t.pnl >= 0
                                ? "text-green-400"
                                : "text-red-400"
                          }`}
                        >
                          {t.pnl === null
                            ? "--"
                            : `${fmtUsd(t.pnl)} (${fmtPct(t.pnlPct ?? 0)})`}
                        </td>
                        <td className="py-2 px-3 text-gray-500 text-xs">
                          {t.reason}
                        </td>
                      </tr>
                    ))}
                    {paginatedTrades.length === 0 && (
                      <tr>
                        <td
                          colSpan={6}
                          className="py-8 text-center text-gray-600 text-sm"
                        >
                          No trades generated
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </main>
    </>
  );
}
