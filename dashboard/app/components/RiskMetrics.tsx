"use client";

import { useState, useEffect, useMemo } from "react";
import LoadingCard from "./LoadingCard";
import { fmt } from "@/app/lib/utils";

/* ════════════════════════════════════════════════════════════════
   RISK METRICS — Portfolio-level risk analytics
   VaR, Beta, Volatility, Max Drawdown, Diversification
   ════════════════════════════════════════════════════════════════ */

interface Holding {
  ticker: string;
  shares: number;
  currentPrice: number;
}

interface RiskMetricsProps {
  holdings: Holding[];
}

interface HistoryBar {
  date: string;
  close: number;
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

/* ── Standard deviation ── */
function stdDev(arr: number[]): number {
  if (arr.length < 2) return 0;
  const mean = arr.reduce((a, b) => a + b, 0) / arr.length;
  const variance =
    arr.reduce((sum, val) => sum + (val - mean) ** 2, 0) / (arr.length - 1);
  return Math.sqrt(variance);
}

/* ── Mean ── */
function mean(arr: number[]): number {
  if (arr.length === 0) return 0;
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

/* ── Max Drawdown from equity curve ── */
function maxDrawdown(prices: number[]): number {
  if (prices.length < 2) return 0;
  let peak = prices[0];
  let maxDd = 0;
  for (const price of prices) {
    if (price > peak) peak = price;
    const dd = (price - peak) / peak;
    if (dd < maxDd) maxDd = dd;
  }
  return maxDd;
}

interface RiskResults {
  var95: number;
  var95Pct: number;
  var99: number;
  var99Pct: number;
  beta: number;
  volatility: number;
  maxDd: number;
  diversification: number;
  totalValue: number;
}

export default function RiskMetrics({ holdings }: RiskMetricsProps) {
  const [priceHistory, setPriceHistory] = useState<Map<string, number[]>>(
    new Map()
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const tickers = useMemo(
    () => holdings.map((h) => h.ticker),
    [holdings]
  );

  // Fetch 90-day history for risk calcs
  useEffect(() => {
    if (tickers.length === 0) return;

    let cancelled = false;

    async function fetchAll() {
      setLoading(true);
      setError(null);

      try {
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
            // skip
          }
          return { ticker, prices: [] as number[] };
        });

        const resolved = await Promise.all(promises);
        if (cancelled) return;

        const map = new Map<string, number[]>();
        for (const { ticker, prices } of resolved) {
          if (prices.length > 1) {
            map.set(ticker, prices);
          }
        }
        setPriceHistory(map);
      } catch {
        if (!cancelled) setError("Failed to fetch price history for risk analysis");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchAll();
    return () => {
      cancelled = true;
    };
  }, [tickers]);

  // Compute risk metrics
  const metrics: RiskResults | null = useMemo(() => {
    if (holdings.length === 0) return null;

    const totalValue = holdings.reduce(
      (sum, h) => sum + h.shares * h.currentPrice,
      0
    );
    if (totalValue <= 0) return null;

    // Compute weights
    const weights: number[] = holdings.map(
      (h) => (h.shares * h.currentPrice) / totalValue
    );

    // Get individual returns
    const individualReturns: number[][] = [];
    const individualVols: number[] = [];

    for (const h of holdings) {
      const prices = priceHistory.get(h.ticker);
      if (prices && prices.length > 1) {
        const rets = pricesToReturns(prices);
        individualReturns.push(rets);
        individualVols.push(stdDev(rets));
      } else {
        individualReturns.push([]);
        individualVols.push(0);
      }
    }

    // Compute portfolio daily returns (weighted)
    // Find minimum common length
    const validLengths = individualReturns
      .map((r) => r.length)
      .filter((l) => l > 0);
    if (validLengths.length === 0)
      return {
        var95: 0,
        var95Pct: 0,
        var99: 0,
        var99Pct: 0,
        beta: 1.0,
        volatility: 0,
        maxDd: 0,
        diversification: 0,
        totalValue,
      };

    const minLen = Math.min(...validLengths);
    const portfolioReturns: number[] = [];

    for (let day = 0; day < minLen; day++) {
      let dayReturn = 0;
      for (let i = 0; i < holdings.length; i++) {
        const rets = individualReturns[i];
        if (rets.length > 0) {
          const idx = rets.length - minLen + day;
          if (idx >= 0 && idx < rets.length) {
            dayReturn += weights[i] * rets[idx];
          }
        }
      }
      portfolioReturns.push(dayReturn);
    }

    // Portfolio stats
    const portMean = mean(portfolioReturns);
    const portStd = stdDev(portfolioReturns);

    // VaR (parametric): VaR = -(mean + z * std) * totalValue
    const z95 = 1.645;
    const z99 = 2.326;
    const var95Pct = -(portMean - z95 * portStd);
    const var99Pct = -(portMean - z99 * portStd);
    const var95 = var95Pct * totalValue;
    const var99 = var99Pct * totalValue;

    // Portfolio Beta: weighted average (default 1.0 per asset)
    const beta = weights.reduce((sum, w) => sum + w * 1.0, 0);

    // Annualized volatility
    const volatility = portStd * Math.sqrt(252);

    // Max drawdown from portfolio equity curve
    const equityCurve: number[] = [totalValue];
    for (const r of portfolioReturns) {
      equityCurve.push(equityCurve[equityCurve.length - 1] * (1 + r));
    }
    const maxDd = maxDrawdown(equityCurve);

    // Diversification ratio: 1 - (portfolio vol / weighted sum of individual vols)
    const weightedSumVols = weights.reduce(
      (sum, w, i) => sum + w * individualVols[i],
      0
    );
    const diversification =
      weightedSumVols > 0 ? 1 - portStd / weightedSumVols : 0;

    return {
      var95,
      var95Pct,
      var99,
      var99Pct,
      beta,
      volatility,
      maxDd,
      diversification: Math.max(0, Math.min(1, diversification)),
      totalValue,
    };
  }, [holdings, priceHistory]);

  // Empty state
  if (holdings.length === 0) {
    return (
      <div className="rounded border border-gray-800/60 bg-[#13131a] p-6">
        <h3 className="text-sm font-semibold text-gray-300 mb-3">
          Portfolio Risk Metrics
        </h3>
        <p className="text-xs text-gray-500">
          Add positions to see risk metrics
        </p>
      </div>
    );
  }

  // Loading state
  if (loading) {
    return <LoadingCard title="Portfolio Risk Metrics" rows={6} />;
  }

  // Error state
  if (error) {
    return (
      <div className="rounded border border-gray-800/60 bg-[#13131a] p-6">
        <h3 className="text-sm font-semibold text-gray-300 mb-3">
          Portfolio Risk Metrics
        </h3>
        <p className="text-xs text-red-400">{error}</p>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="rounded border border-gray-800/60 bg-[#13131a] p-6">
        <h3 className="text-sm font-semibold text-gray-300 mb-3">
          Portfolio Risk Metrics
        </h3>
        <p className="text-xs text-gray-500">
          Waiting for price data to compute risk metrics
        </p>
      </div>
    );
  }

  const rows = [
    {
      label: "Daily VaR (95%)",
      value: `-${fmt.usd(Math.abs(metrics.var95))}`,
      detail: `(-${(metrics.var95Pct * 100).toFixed(2)}%)`,
      color: "text-[#ef4444]",
    },
    {
      label: "Daily VaR (99%)",
      value: `-${fmt.usd(Math.abs(metrics.var99))}`,
      detail: `(-${(metrics.var99Pct * 100).toFixed(2)}%)`,
      color: "text-[#ef4444]",
    },
    {
      label: "Portfolio Beta",
      value: metrics.beta.toFixed(2),
      detail: null,
      color: "text-gray-200",
    },
    {
      label: "Volatility (ann.)",
      value: `${(metrics.volatility * 100).toFixed(1)}%`,
      detail: null,
      color:
        metrics.volatility > 0.3
          ? "text-[#ef4444]"
          : metrics.volatility > 0.2
            ? "text-yellow-400"
            : "text-gray-200",
    },
    {
      label: "Max Drawdown",
      value: `${(metrics.maxDd * 100).toFixed(1)}%`,
      detail: null,
      color: "text-[#ef4444]",
    },
    {
      label: "Diversification",
      value: metrics.diversification.toFixed(2),
      detail: null,
      color:
        metrics.diversification > 0.5
          ? "text-[#22c55e]"
          : metrics.diversification > 0.2
            ? "text-yellow-400"
            : "text-gray-400",
    },
  ];

  return (
    <div className="rounded border border-gray-800/60 bg-[#13131a] p-5">
      <h3 className="text-sm font-semibold text-gray-300 mb-4">
        Portfolio Risk Metrics
      </h3>
      <p className="text-[10px] text-gray-600 mb-3">
        Based on 90-day daily returns &middot; Portfolio value:{" "}
        {fmt.usd(metrics.totalValue)}
      </p>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-x-6 gap-y-3">
        {rows.map((row) => (
          <div key={row.label} className="flex flex-col">
            <span className="text-[10px] text-gray-500 uppercase tracking-wider">
              {row.label}
            </span>
            <div className="flex items-baseline gap-1.5 mt-0.5">
              <span className={`text-sm font-mono font-bold ${row.color}`}>
                {row.value}
              </span>
              {row.detail && (
                <span className="text-[10px] font-mono text-gray-500">
                  {row.detail}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
