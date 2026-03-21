"use client";

import { useState, useEffect, useMemo } from "react";
import LoadingCard from "./LoadingCard";

/* ════════════════════════════════════════════════════════════════
   CORRELATION MATRIX — Pairwise correlation heatmap
   Shows Pearson correlation between portfolio holdings
   ════════════════════════════════════════════════════════════════ */

interface CorrelationMatrixProps {
  tickers: string[];
}

interface HistoryBar {
  date: string;
  close: number;
}

/* ── Pearson correlation ── */
function pearsonCorrelation(x: number[], y: number[]): number {
  const n = Math.min(x.length, y.length);
  if (n < 5) return 0;
  const meanX = x.slice(0, n).reduce((a, b) => a + b, 0) / n;
  const meanY = y.slice(0, n).reduce((a, b) => a + b, 0) / n;
  let num = 0,
    denX = 0,
    denY = 0;
  for (let i = 0; i < n; i++) {
    const dx = x[i] - meanX,
      dy = y[i] - meanY;
    num += dx * dy;
    denX += dx * dx;
    denY += dy * dy;
  }
  const den = Math.sqrt(denX * denY);
  return den === 0 ? 0 : num / den;
}

/* ── Convert prices to daily returns ── */
function pricesToReturns(prices: number[]): number[] {
  const returns: number[] = [];
  for (let i = 1; i < prices.length; i++) {
    if (prices[i - 1] !== 0) {
      returns.push((prices[i] - prices[i - 1]) / prices[i - 1]);
    }
  }
  return returns;
}

/* ── Correlation to CSS color ── */
function correlationColor(value: number): string {
  // +1.0 = dark green, 0.0 = gray, -1.0 = dark red
  if (value >= 0) {
    const intensity = Math.min(value, 1);
    const r = Math.round(30 + (1 - intensity) * 90);
    const g = Math.round(80 + intensity * 100);
    const b = Math.round(30 + (1 - intensity) * 90);
    return `rgb(${r}, ${g}, ${b})`;
  } else {
    const intensity = Math.min(Math.abs(value), 1);
    const r = Math.round(80 + intensity * 100);
    const g = Math.round(30 + (1 - intensity) * 90);
    const b = Math.round(30 + (1 - intensity) * 90);
    return `rgb(${r}, ${g}, ${b})`;
  }
}

function correlationTextColor(value: number): string {
  const abs = Math.abs(value);
  return abs > 0.5 ? "rgba(255,255,255,0.9)" : "rgba(200,200,200,0.8)";
}

export default function CorrelationMatrix({ tickers }: CorrelationMatrixProps) {
  const [priceData, setPriceData] = useState<Map<string, number[]>>(new Map());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch 90-day history for each ticker
  useEffect(() => {
    if (tickers.length === 0) return;

    let cancelled = false;

    async function fetchAll() {
      setLoading(true);
      setError(null);

      try {
        const results = new Map<string, number[]>();

        // Fetch in parallel
        const promises = tickers.map(async (ticker) => {
          try {
            const resp = await fetch(
              `/api/history?code=${encodeURIComponent(ticker)}&range=3m`
            );
            const data: HistoryBar[] = await resp.json();
            if (Array.isArray(data)) {
              return {
                ticker,
                prices: data.map((bar) => bar.close).filter((p) => p > 0),
              };
            }
          } catch {
            // skip failed tickers
          }
          return { ticker, prices: [] as number[] };
        });

        const resolved = await Promise.all(promises);
        if (cancelled) return;

        for (const { ticker, prices } of resolved) {
          if (prices.length > 0) {
            results.set(ticker, prices);
          }
        }

        setPriceData(results);
      } catch {
        if (!cancelled) setError("Failed to fetch price history");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchAll();
    return () => {
      cancelled = true;
    };
  }, [tickers]);

  // Compute correlation matrix
  const matrix = useMemo(() => {
    if (tickers.length === 0) return [];

    const returnsMap = new Map<string, number[]>();
    for (const ticker of tickers) {
      const prices = priceData.get(ticker);
      if (prices && prices.length > 1) {
        returnsMap.set(ticker, pricesToReturns(prices));
      }
    }

    const validTickers = tickers.filter((t) => returnsMap.has(t));
    const n = validTickers.length;

    const grid: { ticker: string; row: { ticker: string; value: number }[] }[] =
      [];

    for (let i = 0; i < n; i++) {
      const row: { ticker: string; value: number }[] = [];
      for (let j = 0; j < n; j++) {
        if (i === j) {
          row.push({ ticker: validTickers[j], value: 1.0 });
        } else {
          const xReturns = returnsMap.get(validTickers[i])!;
          const yReturns = returnsMap.get(validTickers[j])!;
          row.push({
            ticker: validTickers[j],
            value: pearsonCorrelation(xReturns, yReturns),
          });
        }
      }
      grid.push({ ticker: validTickers[i], row });
    }

    return grid;
  }, [tickers, priceData]);

  // Empty state
  if (tickers.length === 0) {
    return (
      <div className="rounded border border-gray-800/60 bg-[#13131a] p-6">
        <h3 className="text-sm font-semibold text-gray-300 mb-3">
          Correlation Matrix
        </h3>
        <p className="text-xs text-gray-500">
          Add positions to see correlations
        </p>
      </div>
    );
  }

  // Loading state
  if (loading) {
    return <LoadingCard title="Correlation Matrix" rows={4} />;
  }

  // Error state
  if (error) {
    return (
      <div className="rounded border border-gray-800/60 bg-[#13131a] p-6">
        <h3 className="text-sm font-semibold text-gray-300 mb-3">
          Correlation Matrix
        </h3>
        <p className="text-xs text-red-400">{error}</p>
      </div>
    );
  }

  // Not enough data
  if (matrix.length < 2) {
    return (
      <div className="rounded border border-gray-800/60 bg-[#13131a] p-6">
        <h3 className="text-sm font-semibold text-gray-300 mb-3">
          Correlation Matrix
        </h3>
        <p className="text-xs text-gray-500">
          Need at least 2 positions with price history to compute correlations
        </p>
      </div>
    );
  }

  return (
    <div className="rounded border border-gray-800/60 bg-[#13131a] p-5">
      <h3 className="text-sm font-semibold text-gray-300 mb-4">
        Correlation Matrix
      </h3>
      <p className="text-[10px] text-gray-600 mb-3">
        Pearson correlation of daily returns (90-day window)
      </p>

      <div
        className="overflow-x-auto"
        style={{ maxHeight: "200px", overflowY: "auto" }}
      >
        <table
          className="border-collapse"
          style={{ fontSize: "11px", lineHeight: "1" }}
        >
          <thead>
            <tr>
              <th className="p-0 w-14" />
              {matrix.map((col) => (
                <th
                  key={col.ticker}
                  className="px-1 py-1.5 text-center font-mono font-normal text-gray-400"
                  style={{ minWidth: "48px", fontSize: "10px" }}
                >
                  {col.ticker.length > 6
                    ? col.ticker.slice(0, 6)
                    : col.ticker}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matrix.map((rowData) => (
              <tr key={rowData.ticker}>
                <td
                  className="px-1 py-1 text-right font-mono text-gray-400 pr-2"
                  style={{ fontSize: "10px" }}
                >
                  {rowData.ticker.length > 6
                    ? rowData.ticker.slice(0, 6)
                    : rowData.ticker}
                </td>
                {rowData.row.map((cell) => (
                  <td
                    key={`${rowData.ticker}-${cell.ticker}`}
                    className="px-1 py-1 text-center font-mono"
                    style={{
                      backgroundColor: correlationColor(cell.value),
                      color: correlationTextColor(cell.value),
                      minWidth: "48px",
                      fontSize: "10px",
                    }}
                    title={`${rowData.ticker} vs ${cell.ticker}: ${cell.value.toFixed(3)}`}
                  >
                    {cell.value.toFixed(2)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-2 mt-3">
        <span className="text-[10px] text-gray-500">-1.0</span>
        <div
          className="flex-1 h-2 rounded"
          style={{
            background:
              "linear-gradient(to right, rgb(180,30,30), rgb(120,120,120), rgb(30,180,30))",
          }}
        />
        <span className="text-[10px] text-gray-500">+1.0</span>
      </div>
    </div>
  );
}
