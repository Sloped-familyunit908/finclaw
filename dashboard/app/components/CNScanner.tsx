"use client";

import { useState } from "react";
import { CN_SCANNER_RESULTS } from "@/app/lib/mockData";
import { SIGNAL_STYLES } from "@/app/lib/utils";
import PriceCard from "./PriceCard";
import { CN_MARKET_DATA } from "@/app/lib/mockData";

type SortField = "score" | "changePct" | "pe";

export default function CNScanner() {
  const [sortBy, setSortBy] = useState<SortField>("score");
  const [filterSignal, setFilterSignal] = useState<string>("all");

  const filtered = CN_SCANNER_RESULTS.filter(
    (r) => filterSignal === "all" || r.signal === filterSignal
  );

  const sorted = [...filtered].sort((a, b) => {
    if (sortBy === "score") return b.score - a.score;
    if (sortBy === "changePct") return b.changePct - a.changePct;
    if (sortBy === "pe") return (a.pe ?? 999) - (b.pe ?? 999);
    return 0;
  });

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-200">
          China A-Shares Scanner
        </h2>
        <p className="text-xs text-gray-500 mt-1">
          Multi-factor scoring: technicals, fundamentals, and sentiment
        </p>
      </div>

      {/* A-share price cards */}
      <div>
        <h3 className="text-sm font-semibold text-gray-400 mb-3">
          Watchlist
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {CN_MARKET_DATA.slice(0, 3).map((m) => (
            <PriceCard key={m.asset} data={m} />
          ))}
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Signal:</span>
          {["all", "strong_buy", "buy", "hold", "sell"].map((sig) => {
            const s =
              sig === "all"
                ? null
                : SIGNAL_STYLES[sig] ?? SIGNAL_STYLES.hold;
            return (
              <button
                key={sig}
                onClick={() => setFilterSignal(sig)}
                className={`px-2 py-1 rounded text-[10px] font-medium border transition-all ${
                  filterSignal === sig
                    ? s
                      ? `${s.text} ${s.bg} ${s.border}`
                      : "text-slate-300 bg-slate-800/60 border-slate-600/50"
                    : "text-gray-500 bg-gray-800/30 border-gray-700/40 hover:text-gray-300"
                }`}
              >
                {sig === "all"
                  ? "All"
                  : sig === "strong_buy"
                    ? "Strong Buy"
                    : sig === "strong_sell"
                      ? "Strong Sell"
                      : sig.charAt(0).toUpperCase() + sig.slice(1)}
              </button>
            );
          })}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Sort:</span>
          {(
            [
              ["score", "Score"],
              ["changePct", "Change %"],
              ["pe", "PE (asc)"],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setSortBy(key)}
              className={`px-2 py-1 rounded text-[10px] border transition-all ${
                sortBy === key
                  ? "text-slate-300 bg-slate-800/60 border-slate-600/50"
                  : "text-gray-500 bg-gray-800/30 border-gray-700/40 hover:text-gray-300"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Scanner results table */}
      <div className="overflow-x-auto rounded border border-gray-800/60">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-900/50 text-gray-400 text-xs uppercase tracking-wider">
              <th className="text-left py-3 px-4">Code</th>
              <th className="text-left py-3 px-3">Name</th>
              <th className="text-left py-3 px-3 hidden sm:table-cell">Sector</th>
              <th className="text-right py-3 px-3">Price</th>
              <th className="text-right py-3 px-3">Change</th>
              <th className="text-right py-3 px-3 hidden md:table-cell">Volume</th>
              <th className="text-right py-3 px-3 hidden md:table-cell">PE</th>
              <th className="text-center py-3 px-3">Signal</th>
              <th className="text-center py-3 px-3">Score</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => {
              const s = SIGNAL_STYLES[r.signal] ?? SIGNAL_STYLES.hold;
              const isUp = r.changePct >= 0;
              return (
                <tr
                  key={r.code}
                  className="border-t border-gray-800/30 hover:bg-gray-900/30"
                >
                  <td className="py-2.5 px-4 font-mono text-xs text-gray-400">
                    {r.code}
                  </td>
                  <td className="py-2.5 px-3 font-medium text-gray-200">
                    {r.name}
                  </td>
                  <td className="py-2.5 px-3 text-gray-500 text-xs hidden sm:table-cell">
                    {r.sector}
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-white">
                    ¥{r.price.toFixed(2)}
                  </td>
                  <td
                    className={`py-2.5 px-3 text-right font-mono ${
                      isUp ? "text-red-400" : "text-green-400"
                    }`}
                  >
                    {isUp ? "+" : ""}
                    {r.changePct.toFixed(2)}%
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-gray-400 text-xs hidden md:table-cell">
                    {r.volume}
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-gray-400 hidden md:table-cell">
                    {r.pe?.toFixed(1) ?? "—"}
                  </td>
                  <td className="py-2.5 px-3 text-center">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${s.text} ${s.bg} border ${s.border}`}
                    >
                      {r.signal === "strong_buy"
                        ? "STRONG BUY"
                        : r.signal === "strong_sell"
                          ? "STRONG SELL"
                          : r.signal.toUpperCase()}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-center">
                    <div className="flex items-center justify-center gap-1">
                      <div className="w-12 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            r.score >= 80
                              ? "bg-green-500"
                              : r.score >= 60
                                ? "bg-yellow-500"
                                : r.score >= 40
                                  ? "bg-slate-400"
                                  : "bg-red-500"
                          }`}
                          style={{ width: `${r.score}%` }}
                        />
                      </div>
                      <span className="text-xs font-mono text-gray-300 w-6 text-right">
                        {r.score}
                      </span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="p-3 bg-gray-800/20 border border-gray-700/30 rounded text-xs text-gray-500">
        Data shown is simulated for demonstration purposes. Live market data integration pending.
        <br />
        <span className="text-gray-600">
          Note: A-share color convention follows China market standard (red = up, green = down)
        </span>
      </div>
    </div>
  );
}
