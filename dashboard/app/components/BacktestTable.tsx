"use client";

import { useMemo, useRef, useEffect } from "react";
import { fmt } from "@/app/lib/utils";
import { BACKTEST_DATA, EQUITY_CURVE_DATA } from "@/app/lib/fallbackData";
import {
  createChart,
  ColorType,
  CrosshairMode,
  LineSeries,
  LineStyle,
} from "lightweight-charts";
import type { IChartApi } from "lightweight-charts";

function EquityCurve() {
  const chartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    const chart: IChartApi = createChart(chartRef.current, {
      width: chartRef.current.clientWidth,
      height: 280,
      layout: {
        background: { type: ColorType.Solid, color: '#13131a' },
        textColor: '#9ca3af',
      },
      grid: {
        vertLines: { color: '#1e1e2e' },
        horzLines: { color: '#1e1e2e' },
      },
      crosshair: { mode: CrosshairMode.Normal },
      timeScale: { borderColor: '#374151' },
      rightPriceScale: { borderColor: '#374151' },
    });

    // Use a base date and add days as dates for the time scale
    const baseDate = new Date('2024-01-01');

    const toDateStr = (day: number) => {
      const d = new Date(baseDate);
      d.setDate(d.getDate() + day);
      return d.toISOString().slice(0, 10);
    };

    const debate3Series = chart.addSeries(LineSeries, {
      color: '#5eead4',
      lineWidth: 2,
      title: '3-Agent Debate',
    });
    debate3Series.setData(
      EQUITY_CURVE_DATA.map((d) => ({
        time: toDateStr(d.day),
        value: d.debate3,
      }))
    );

    const debate2Series = chart.addSeries(LineSeries, {
      color: '#94a3b8',
      lineWidth: 2,
      title: '2-Agent Debate',
    });
    debate2Series.setData(
      EQUITY_CURVE_DATA.map((d) => ({
        time: toDateStr(d.day),
        value: d.debate2,
      }))
    );

    const buyHoldSeries = chart.addSeries(LineSeries, {
      color: '#6b7280',
      lineWidth: 2,
      lineStyle: LineStyle.Dashed,
      title: 'Buy & Hold',
    });
    buyHoldSeries.setData(
      EQUITY_CURVE_DATA.map((d) => ({
        time: toDateStr(d.day),
        value: d.buyHold,
      }))
    );

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (chartRef.current) {
        chart.applyOptions({ width: chartRef.current.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, []);

  return (
    <div className="rounded border border-gray-800/60 bg-[#13131a] p-4 sm:p-5">
      <h3 className="text-sm font-semibold text-gray-400 mb-4">
        Strategy Equity Curves (200-day Bear Market)
      </h3>
      <div ref={chartRef} />
    </div>
  );
}

export default function BacktestTable() {
  const sorted = useMemo(
    () => [...BACKTEST_DATA].sort((a, b) => b.alpha - a.alpha),
    []
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h2 className="text-lg font-semibold text-gray-200">Backtest Performance</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Historical backtest results from BTC/ETH/SOL 200-day analysis
          </p>
        </div>
        <span className="text-xs text-gray-500">
          200 days, bear market, BTC/ETH/SOL
        </span>
      </div>

      <EquityCurve />

      <div className="overflow-x-auto rounded border border-gray-800/60">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-900/50 text-gray-400 text-xs uppercase tracking-wider">
              <th className="text-left py-3 px-4">Strategy</th>
              <th className="text-left py-3 px-3">Asset</th>
              <th className="text-right py-3 px-3">Return</th>
              <th className="text-right py-3 px-3">Alpha</th>
              <th className="text-right py-3 px-3">Sharpe</th>
              <th className="text-right py-3 px-3 hidden sm:table-cell">
                Max DD
              </th>
              <th className="text-right py-3 px-3 hidden md:table-cell">
                Trades
              </th>
              <th className="text-center py-3 px-3 hidden md:table-cell">
                Sig.
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((r, i) => (
              <tr
                key={`${r.strategy}-${r.asset}`}
                className={`border-t border-gray-800/30 ${
                  i === 0
                    ? "bg-gray-800/20"
                    : "hover:bg-gray-900/30"
                }`}
              >
                <td className="py-2.5 px-4 font-medium text-gray-200">
                  {r.strategy}
                </td>
                <td className="py-2.5 px-3 text-gray-400">{r.asset}</td>
                <td
                  className={`py-2.5 px-3 text-right font-mono ${
                    r.totalReturn >= 0 ? "text-green-400" : "text-red-400"
                  }`}
                >
                  {fmt.pct(r.totalReturn)}
                </td>
                <td
                  className={`py-2.5 px-3 text-right font-mono ${
                    r.alpha > 0 ? "text-green-400" : "text-gray-400"
                  }`}
                >
                  {fmt.pct(r.alpha)}
                </td>
                <td className="py-2.5 px-3 text-right font-mono text-gray-300">
                  {r.sharpe.toFixed(2)}
                </td>
                <td className="py-2.5 px-3 text-right font-mono text-red-400 hidden sm:table-cell">
                  {fmt.pct(r.maxDD)}
                </td>
                <td className="py-2.5 px-3 text-right font-mono text-gray-400 hidden md:table-cell">
                  {r.trades}
                </td>
                <td className="py-2.5 px-3 text-center hidden md:table-cell text-gray-400">
                  {r.isSignificant ? "Yes" : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="p-3 bg-gray-800/20 border border-gray-700/30 rounded text-xs text-gray-500">
        3-Agent Debate preserved capital (-1.0% avg) vs Buy &amp; Hold (-50%
        avg) in a 200-day bear market. Alpha: +38% to +61%. Note: Low trade
        count — needs more data for statistical significance.
      </div>
    </div>
  );
}
