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
    // pe: nulls last
    if (sortBy === "pe") return (a.pe ?? 999) - (b.pe ?? 999);
    return 0;
  });

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold flex items-center gap-2">
          🇨🇳 A股 Scanner
          <span className="text-sm font-normal text-gray-500">
            — 沪深市场智能扫描
          </span>
        </h2>
        <p className="text-xs text-gray-500 mt-1">
          AI agent 多维度打分 · 技术面 + 基本面 + 情绪面综合评估
        </p>
      </div>

      {/* A-share price cards */}
      <div>
        <h3 className="text-sm font-semibold text-gray-400 mb-3">
          📋 重点跟踪
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
                      : "text-orange-400 bg-orange-950/40 border-orange-800/50"
                    : "text-gray-500 bg-gray-800/30 border-gray-700/40 hover:text-gray-300"
                }`}
              >
                {sig === "all"
                  ? "All"
                  : sig.replace("_", " ").toUpperCase()}
              </button>
            );
          })}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Sort:</span>
          {(
            [
              ["score", "综合评分"],
              ["changePct", "涨跌幅"],
              ["pe", "PE (低→高)"],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setSortBy(key)}
              className={`px-2 py-1 rounded text-[10px] border transition-all ${
                sortBy === key
                  ? "text-orange-400 bg-orange-950/40 border-orange-800/50"
                  : "text-gray-500 bg-gray-800/30 border-gray-700/40 hover:text-gray-300"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Scanner results table */}
      <div className="overflow-x-auto rounded-xl border border-gray-800/60">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-900/50 text-gray-400 text-xs uppercase tracking-wider">
              <th className="text-left py-3 px-4">代码</th>
              <th className="text-left py-3 px-3">名称</th>
              <th className="text-left py-3 px-3 hidden sm:table-cell">板块</th>
              <th className="text-right py-3 px-3">现价</th>
              <th className="text-right py-3 px-3">涨跌</th>
              <th className="text-right py-3 px-3 hidden md:table-cell">成交量</th>
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
                      {r.signal.replace("_", " ")}
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
                                  ? "bg-orange-500"
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

      <div className="p-3 bg-orange-950/15 border border-orange-800/30 rounded-lg text-xs text-orange-400">
        🦀 FinClaw A股扫描器 — 数据为模拟数据，仅供演示。接入实时行情后可自动更新。
        <br />
        <span className="text-gray-500">
          注: A股涨跌色标遵循中国市场惯例（红涨绿跌）
        </span>
      </div>
    </div>
  );
}
