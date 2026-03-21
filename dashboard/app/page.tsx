"use client";

import { useState, useEffect } from "react";
import type { TabId, MarketData } from "@/app/types";
import {
  MARKET_DATA,
  US_MARKET_DATA,
  CN_MARKET_DATA,
  DEBATE,
} from "@/app/lib/mockData";

import Header from "@/app/components/Header";
import PriceCard from "@/app/components/PriceCard";
import DebateArena from "@/app/components/DebateArena";
import BacktestTable from "@/app/components/BacktestTable";
import AgentLeaderboard from "@/app/components/AgentLeaderboard";
import StrategyGallery from "@/app/components/StrategyGallery";
import RiskPanel from "@/app/components/RiskPanel";
import CNScanner from "@/app/components/CNScanner";

/* ── Loading skeleton for price cards ── */
function PriceCardSkeleton() {
  return (
    <div className="rounded-xl border border-gray-800/60 bg-[#13131a] p-4 sm:p-5 animate-pulse">
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1">
          <div className="h-5 w-24 bg-gray-800 rounded mb-2" />
          <div className="h-8 w-32 bg-gray-800 rounded" />
        </div>
        <div className="h-8 w-20 bg-gray-800 rounded-lg" />
      </div>
      <div className="grid grid-cols-2 gap-y-2 gap-x-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="flex justify-between">
            <div className="h-3 w-12 bg-gray-800/60 rounded" />
            <div className="h-3 w-16 bg-gray-800/60 rounded" />
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Home() {
  const [tab, setTab] = useState<TabId>("overview");

  const [usData, setUsData] = useState<MarketData[]>(US_MARKET_DATA);
  const [cnData, setCnData] = useState<MarketData[]>(CN_MARKET_DATA);
  const [cryptoData, setCryptoData] = useState<MarketData[]>(MARKET_DATA);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function fetchAll() {
      setLoading(true);

      const fetchers = [
        fetch("/api/prices?market=us")
          .then((r) => r.json())
          .catch(() => US_MARKET_DATA),
        fetch("/api/prices?market=cn")
          .then((r) => r.json())
          .catch(() => CN_MARKET_DATA),
        fetch("/api/prices?market=crypto")
          .then((r) => r.json())
          .catch(() => MARKET_DATA),
      ];

      const [us, cn, crypto] = await Promise.all(fetchers);

      if (!cancelled) {
        setUsData(us);
        setCnData(cn);
        setCryptoData(crypto);
        setLoading(false);
      }
    }

    fetchAll();

    // Refresh every 60 seconds
    const interval = setInterval(fetchAll, 60_000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const renderCards = (data: MarketData[], count?: number) => {
    const items = count ? data.slice(0, count) : data;
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.map((m) => (
          <PriceCard key={m.asset} data={m} />
        ))}
      </div>
    );
  };

  const renderSkeletons = (n: number) => (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: n }).map((_, i) => (
        <PriceCardSkeleton key={i} />
      ))}
    </div>
  );

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-gray-100">
      <Header tab={tab} setTab={setTab} />

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {tab === "overview" && (
          <div className="space-y-8">
            {/* US Stocks */}
            <section>
              <h2 className="text-lg font-semibold mb-4 text-gray-300">
                🇺🇸 US Stocks
              </h2>
              {loading ? renderSkeletons(3) : renderCards(usData.slice(0, 3))}
              <div className="mt-4">
                {loading
                  ? renderSkeletons(usData.length - 3)
                  : renderCards(usData.slice(3))}
              </div>
            </section>

            {/* Crypto */}
            <section>
              <h2 className="text-lg font-semibold mb-4 text-gray-300">
                ₿ Crypto Market
              </h2>
              {loading ? renderSkeletons(3) : renderCards(cryptoData)}
            </section>

            {/* A-Shares */}
            <section>
              <h2 className="text-lg font-semibold mb-4 text-gray-300">
                🇨🇳 A-Share Market
              </h2>
              {loading ? renderSkeletons(3) : renderCards(cnData.slice(0, 3))}
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
