"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import LoadingCard, { LoadingTable } from "@/app/components/LoadingCard";

/* ════════════════════════════════════════════════════════════════
   TYPES
   ════════════════════════════════════════════════════════════════ */

interface TimelinePoint {
  generation: number;
  timestamp: string;
  bestFitness: number;
  annualReturn: number;
  sharpe: number;
  maxDrawdown: number;
  winRate: number;
  calmar: number;
  totalTrades: number;
  profitFactor: number;
}

interface TopStrategy {
  generation: number;
  annual_return: number;
  max_drawdown: number;
  win_rate: number;
  sharpe: number;
  calmar: number;
  total_trades: number;
  profit_factor: number;
  fitness: number;
  dna: Record<string, number>;
}

interface HistoryData {
  timeline: TimelinePoint[];
  topStrategies: TopStrategy[];
  totalGenerations: number;
}

/* ════════════════════════════════════════════════════════════════
   SVG LINE CHART — pure SVG, dark theme
   ════════════════════════════════════════════════════════════════ */

type MetricKey = "bestFitness" | "annualReturn" | "sharpe" | "maxDrawdown";

const METRIC_CONFIG: Record<MetricKey, { label: string; color: string; format: (n: number) => string }> = {
  bestFitness:  { label: "Fitness",       color: "#22c55e", format: (n) => n.toFixed(1) },
  annualReturn: { label: "Annual Return", color: "#5eead4", format: (n) => n.toFixed(1) + "%" },
  sharpe:       { label: "Sharpe",        color: "#a78bfa", format: (n) => n.toFixed(2) },
  maxDrawdown:  { label: "Max Drawdown",  color: "#ef4444", format: (n) => n.toFixed(1) + "%" },
};

function EvolutionChart({
  data,
  metric,
}: {
  data: TimelinePoint[];
  metric: MetricKey;
}) {
  const W = 800;
  const H = 300;
  const PAD_L = 60;
  const PAD_R = 20;
  const PAD_T = 20;
  const PAD_B = 40;
  const plotW = W - PAD_L - PAD_R;
  const plotH = H - PAD_T - PAD_B;

  const config = METRIC_CONFIG[metric];

  const values = data.map((d) => d[metric]);
  const gens = data.map((d) => d.generation);

  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);
  const range = maxVal - minVal || 1;
  const padding = range * 0.05;
  const yMin = minVal - padding;
  const yMax = maxVal + padding;
  const yRange = yMax - yMin;

  const genMin = gens[0];
  const genMax = gens[gens.length - 1];
  const genRange = genMax - genMin || 1;

  const toX = (gen: number) => PAD_L + ((gen - genMin) / genRange) * plotW;
  const toY = (val: number) => PAD_T + plotH - ((val - yMin) / yRange) * plotH;

  // Build path
  const pathD = data
    .map((d, i) => {
      const x = toX(d.generation);
      const y = toY(d[metric]);
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  // Fill area path
  const areaD = pathD +
    ` L${toX(genMax).toFixed(1)},${(PAD_T + plotH).toFixed(1)}` +
    ` L${toX(genMin).toFixed(1)},${(PAD_T + plotH).toFixed(1)} Z`;

  // Y-axis ticks
  const yTicks = 5;
  const yTickValues = Array.from({ length: yTicks + 1 }, (_, i) =>
    yMin + (yRange * i) / yTicks
  );

  // X-axis ticks
  const xTicks = Math.min(data.length, 6);
  const xTickIndices = Array.from({ length: xTicks }, (_, i) =>
    Math.round((i / (xTicks - 1)) * (data.length - 1))
  );

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="w-full"
      style={{ maxWidth: W, background: "#0a0a0f" }}
    >
      {/* Grid lines */}
      {yTickValues.map((v, i) => (
        <line
          key={`grid-${i}`}
          x1={PAD_L}
          y1={toY(v)}
          x2={W - PAD_R}
          y2={toY(v)}
          stroke="#1f2937"
          strokeWidth={0.5}
        />
      ))}

      {/* Area fill */}
      <path
        d={areaD}
        fill={config.color}
        fillOpacity={0.06}
      />

      {/* Line */}
      <path
        d={pathD}
        fill="none"
        stroke={config.color}
        strokeWidth={1.5}
        strokeLinejoin="round"
      />

      {/* Latest point dot */}
      {data.length > 0 && (
        <circle
          cx={toX(data[data.length - 1].generation)}
          cy={toY(data[data.length - 1][metric])}
          r={3}
          fill={config.color}
        />
      )}

      {/* Y-axis labels */}
      {yTickValues.map((v, i) => (
        <text
          key={`y-${i}`}
          x={PAD_L - 8}
          y={toY(v) + 3}
          textAnchor="end"
          fill="#6b7280"
          fontSize={10}
          fontFamily="monospace"
        >
          {config.format(v)}
        </text>
      ))}

      {/* X-axis labels */}
      {xTickIndices.map((idx) => (
        <text
          key={`x-${idx}`}
          x={toX(data[idx].generation)}
          y={H - 8}
          textAnchor="middle"
          fill="#6b7280"
          fontSize={10}
          fontFamily="monospace"
        >
          Gen {data[idx].generation}
        </text>
      ))}

      {/* Axis labels */}
      <text
        x={PAD_L + plotW / 2}
        y={H - 0}
        textAnchor="middle"
        fill="#4b5563"
        fontSize={10}
      >
        Generation
      </text>
    </svg>
  );
}

/* ════════════════════════════════════════════════════════════════
   DNA PARAMETER TABLE
   ════════════════════════════════════════════════════════════════ */

function DNADisplay({ dna }: { dna: Record<string, number> }) {
  const [expanded, setExpanded] = useState(false);
  const entries = Object.entries(dna);
  const shown = expanded ? entries : entries.slice(0, 6);

  return (
    <div>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-1">
        {shown.map(([key, value]) => (
          <div key={key} className="flex justify-between text-xs py-0.5">
            <span className="text-gray-500 truncate mr-2">{key}</span>
            <span className="font-mono text-gray-300 shrink-0">
              {typeof value === "number" ? value.toFixed(4) : String(value)}
            </span>
          </div>
        ))}
      </div>
      {entries.length > 6 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-[10px] text-gray-600 hover:text-gray-400 mt-1 transition-colors"
        >
          {expanded ? "Show less" : `Show all ${entries.length} parameters`}
        </button>
      )}
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════
   EVOLUTION PAGE
   ════════════════════════════════════════════════════════════════ */

export default function EvolutionPage() {
  const [data, setData] = useState<HistoryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedMetric, setSelectedMetric] = useState<MetricKey>("bestFitness");

  useEffect(() => {
    let cancelled = false;

    async function fetchHistory() {
      try {
        const resp = await fetch("/api/evolution/history");
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const json = await resp.json();
        if (!cancelled) {
          setData(json);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load evolution data");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchHistory();
    return () => { cancelled = true; };
  }, []);

  // Summary stats
  const summary = useMemo(() => {
    if (!data || data.timeline.length === 0) return null;
    const latest = data.timeline[data.timeline.length - 1];
    const first = data.timeline[0];
    return {
      currentGen: latest.generation,
      currentFitness: latest.bestFitness,
      fitnessImprovement: ((latest.bestFitness - first.bestFitness) / (first.bestFitness || 1)) * 100,
      bestReturn: Math.max(...data.timeline.map((d) => d.annualReturn)),
      bestSharpe: Math.max(...data.timeline.map((d) => d.sharpe)),
      lowestDrawdown: Math.min(...data.timeline.map((d) => d.maxDrawdown)),
      dataPoints: data.timeline.length,
    };
  }, [data]);

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
              Evolution Engine
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
        {/* Loading state */}
        {loading && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <LoadingCard key={i} rows={2} />
              ))}
            </div>
            <LoadingCard chart chartHeight={300} rows={0} title="chart" />
            <LoadingTable columns={7} rows={5} />
          </div>
        )}

        {/* Error state */}
        {error && !loading && (
          <div className="rounded border border-red-900/40 bg-red-950/20 p-6 text-center">
            <p className="text-red-400 text-sm">{error}</p>
            <p className="text-gray-600 text-xs mt-2">
              Check that the evolution engine has generated results in ../evolution_results/
            </p>
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && (!data || data.timeline.length === 0) && (
          <div className="rounded border border-gray-800/60 bg-[#13131a] p-12 text-center">
            <p className="text-gray-400 text-sm">No evolution data found</p>
            <p className="text-gray-600 text-xs mt-2">
              Run the evolution engine to generate gen_XXXX.json files in ../evolution_results/
            </p>
            <p className="text-gray-700 text-[10px] mt-4 font-mono">
              python -m finclaw.evolution.engine --generations 100
            </p>
          </div>
        )}

        {/* Loaded state */}
        {!loading && !error && data && data.timeline.length > 0 && summary && (
          <>
            {/* Summary cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="rounded border border-gray-800/60 bg-[#13131a] p-4">
                <p className="text-xs text-gray-500 mb-1">Current Generation</p>
                <p className="text-2xl font-mono font-bold text-white">
                  {summary.currentGen.toLocaleString()}
                </p>
                <p className="text-[10px] text-gray-600 mt-1">
                  {summary.dataPoints} checkpoints
                </p>
              </div>
              <div className="rounded border border-gray-800/60 bg-[#13131a] p-4">
                <p className="text-xs text-gray-500 mb-1">Best Fitness</p>
                <p className="text-2xl font-mono font-bold text-[#22c55e]">
                  {summary.currentFitness.toFixed(1)}
                </p>
                <p className="text-[10px] text-gray-600 mt-1">
                  {summary.fitnessImprovement >= 0 ? "+" : ""}
                  {summary.fitnessImprovement.toFixed(0)}% from gen 1
                </p>
              </div>
              <div className="rounded border border-gray-800/60 bg-[#13131a] p-4">
                <p className="text-xs text-gray-500 mb-1">Peak Annual Return</p>
                <p className="text-2xl font-mono font-bold text-[#5eead4]">
                  {summary.bestReturn.toFixed(1)}%
                </p>
                <p className="text-[10px] text-gray-600 mt-1">
                  Best Sharpe: {summary.bestSharpe.toFixed(2)}
                </p>
              </div>
              <div className="rounded border border-gray-800/60 bg-[#13131a] p-4">
                <p className="text-xs text-gray-500 mb-1">Lowest Drawdown</p>
                <p className="text-2xl font-mono font-bold text-gray-200">
                  {summary.lowestDrawdown.toFixed(1)}%
                </p>
                <p className="text-[10px] text-gray-600 mt-1">
                  Across all generations
                </p>
              </div>
            </div>

            {/* Chart section */}
            <section className="rounded border border-gray-800/60 bg-[#13131a] p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
                  Evolution Progress
                </h2>
                <div className="flex gap-1">
                  {(Object.keys(METRIC_CONFIG) as MetricKey[]).map((key) => (
                    <button
                      key={key}
                      onClick={() => setSelectedMetric(key)}
                      className={`px-2 py-1 text-[10px] rounded transition-colors ${
                        selectedMetric === key
                          ? "bg-gray-700/60 text-white border border-gray-600/50"
                          : "text-gray-500 hover:text-gray-300 hover:bg-gray-800/40"
                      }`}
                    >
                      {METRIC_CONFIG[key].label}
                    </button>
                  ))}
                </div>
              </div>

              <EvolutionChart data={data.timeline} metric={selectedMetric} />

              <div className="flex items-center gap-4 mt-3 text-[10px] text-gray-600">
                <span>
                  Latest: {METRIC_CONFIG[selectedMetric].format(
                    data.timeline[data.timeline.length - 1][selectedMetric]
                  )}
                </span>
                <span>|</span>
                <span>
                  {data.timeline.length} data points across{" "}
                  {data.totalGenerations.toLocaleString()} generations
                </span>
              </div>
            </section>

            {/* Top 5 strategies table */}
            <section>
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
                Top 5 Current Strategies (Gen {data.totalGenerations})
              </h2>
              <div className="space-y-3">
                {data.topStrategies.map((strategy, i) => (
                  <div
                    key={i}
                    className="rounded border border-gray-800/60 bg-[#13131a] p-4"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <span className="text-xs font-mono bg-gray-800/60 text-gray-300 px-2 py-1 rounded">
                          #{i + 1}
                        </span>
                        <span className="text-sm font-mono font-bold text-white">
                          Fitness: {strategy.fitness.toFixed(2)}
                        </span>
                      </div>
                      <div className="flex gap-4 text-xs">
                        <span className={`font-mono ${strategy.annual_return >= 0 ? "text-[#22c55e]" : "text-[#ef4444]"}`}>
                          {strategy.annual_return >= 0 ? "+" : ""}{strategy.annual_return.toFixed(1)}% return
                        </span>
                        <span className="font-mono text-gray-400">
                          Sharpe {strategy.sharpe.toFixed(2)}
                        </span>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-6 gap-y-2 text-xs mb-3">
                      <div className="flex justify-between">
                        <span className="text-gray-500">Max DD</span>
                        <span className="font-mono text-[#ef4444]">
                          {strategy.max_drawdown.toFixed(1)}%
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Win Rate</span>
                        <span className="font-mono text-gray-300">
                          {strategy.win_rate.toFixed(1)}%
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Calmar</span>
                        <span className="font-mono text-gray-300">
                          {strategy.calmar.toFixed(2)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Trades</span>
                        <span className="font-mono text-gray-300">
                          {strategy.total_trades}
                        </span>
                      </div>
                    </div>

                    <div className="border-t border-gray-800/40 pt-3">
                      <p className="text-[10px] text-gray-600 mb-2 uppercase tracking-wider">
                        DNA Parameters
                      </p>
                      <DNADisplay dna={strategy.dna} />
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </>
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
