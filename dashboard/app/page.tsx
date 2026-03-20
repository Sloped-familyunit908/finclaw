"use client";

import { useState } from "react";
import type { TabId } from "@/app/types";
import { MARKET_DATA, CN_MARKET_DATA, DEBATE } from "@/app/lib/mockData";

import Header from "@/app/components/Header";
import PriceCard from "@/app/components/PriceCard";
import DebateArena from "@/app/components/DebateArena";
import BacktestTable from "@/app/components/BacktestTable";
import AgentLeaderboard from "@/app/components/AgentLeaderboard";
import StrategyGallery from "@/app/components/StrategyGallery";
import RiskPanel from "@/app/components/RiskPanel";
import CNScanner from "@/app/components/CNScanner";

export default function Home() {
  const [tab, setTab] = useState<TabId>("overview");

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-gray-100">
      <Header tab={tab} setTab={setTab} />

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {tab === "overview" && (
          <div className="space-y-8">
            {/* Crypto */}
            <section>
              <h2 className="text-lg font-semibold mb-4 text-gray-300">
                🌍 Crypto Market
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {MARKET_DATA.map((m) => (
                  <PriceCard key={m.asset} data={m} />
                ))}
              </div>
            </section>

            {/* A-Shares */}
            <section>
              <h2 className="text-lg font-semibold mb-4 text-gray-300">
                🇨🇳 A股市场
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {CN_MARKET_DATA.slice(0, 3).map((m) => (
                  <PriceCard key={m.asset} data={m} />
                ))}
              </div>
            </section>

            <DebateArena debate={DEBATE} />
            <BacktestTable />
          </div>
        )}
        {tab === "arena" && <DebateArena debate={DEBATE} />}
        {tab === "backtest" && <BacktestTable />}
        {tab === "cn-scanner" && <CNScanner />}
        {tab === "strategies" && <StrategyGallery />}
        {tab === "agents" && <AgentLeaderboard />}
        {tab === "risk" && <RiskPanel />}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800/30 py-6 mt-12">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <p className="text-xs text-gray-600">
            Built with 🦀 by{" "}
            <span className="text-orange-500/70">NeuZhou</span> — Python +
            TypeScript + AI Agents
          </p>
          <p className="text-[10px] text-gray-700 mt-1">
            Research: Multi-Agent Debate (Du et al. 2023) · R&D-Agent-Quant
            (NeurIPS 2025) · StockAgent (2024)
          </p>
        </div>
      </footer>
    </div>
  );
}
