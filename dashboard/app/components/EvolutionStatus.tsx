"use client";

import { useState, useEffect } from "react";

interface EvolutionData {
  generation: number;
  timestamp: string;
  bestFitness: number;
  annualReturn: number;
  sharpe: number;
  winRate: number;
  dimensions: number;
  stockCount: number;
}

export default function EvolutionStatus() {
  const [data, setData] = useState<EvolutionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [empty, setEmpty] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function fetchEvolution() {
      try {
        const resp = await fetch("/api/evolution");
        const json = await resp.json();

        if (cancelled) return;

        if (json && json.generation != null) {
          setData(json);
          setEmpty(false);
        } else {
          setData(null);
          setEmpty(true);
        }
      } catch {
        if (!cancelled) {
          setData(null);
          setEmpty(true);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchEvolution();
    const interval = setInterval(fetchEvolution, 30_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  return (
    <div className="rounded border border-gray-800/60 bg-[#13131a] p-4">
      <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
        Evolution Engine
      </h3>

      {loading ? (
        <div className="space-y-2 animate-pulse">
          <div className="h-4 w-24 bg-gray-800 rounded" />
          <div className="h-3 w-32 bg-gray-800 rounded" />
          <div className="h-3 w-28 bg-gray-800 rounded" />
        </div>
      ) : empty || !data ? (
        <div>
          <p className="text-xs text-gray-500 leading-relaxed">
            Run the evolution engine to see results here
          </p>
          <p className="text-[10px] text-gray-600 mt-2">
            Genetic algorithm optimization for trading strategies
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Generation</span>
            <span className="font-mono text-gray-200 font-bold">
              {data.generation.toLocaleString()}
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Annual Return</span>
            <span
              className={`font-mono font-bold ${
                data.annualReturn >= 0 ? "text-[#22c55e]" : "text-[#ef4444]"
              }`}
            >
              {data.annualReturn >= 0 ? "+" : ""}
              {data.annualReturn.toFixed(1)}%
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Sharpe</span>
            <span className="font-mono text-gray-200">
              {data.sharpe.toFixed(2)}
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Win Rate</span>
            <span className="font-mono text-gray-200">
              {(data.winRate * 100).toFixed(1)}%
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Fitness</span>
            <span className="font-mono text-gray-200">
              {data.bestFitness.toFixed(4)}
            </span>
          </div>
          <div className="pt-2 border-t border-gray-800/40 mt-2">
            <p className="text-[10px] text-gray-600 font-mono">
              {data.dimensions} dimensions | {data.stockCount} stocks | 24/7
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
