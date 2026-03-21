"use client";

import { useState, useEffect, useMemo } from "react";
import type { TabId, MarketData } from "@/app/types";
import {
  CRYPTO_TICKERS,
  US_TICKERS,
  CN_TICKERS,
  DEBATE,
} from "@/app/lib/fallbackData";

import Header from "@/app/components/Header";
import PriceCard from "@/app/components/PriceCard";
import DebateArena from "@/app/components/DebateArena";
import BacktestTable from "@/app/components/BacktestTable";
import AgentLeaderboard from "@/app/components/AgentLeaderboard";
import StrategyGallery from "@/app/components/StrategyGallery";
import RiskPanel from "@/app/components/RiskPanel";
import CNScanner from "@/app/components/CNScanner";

/* -- Loading skeleton for price cards -- */
function PriceCardSkeleton() {
  return (
    <div className="rounded border border-gray-800/60 bg-[#13131a] px-3 py-2.5 animate-pulse">
      <div className="flex justify-between items-start mb-1.5">
        <div className="flex-1">
          <div className="h-4 w-24 bg-gray-800 rounded mb-1" />
          <div className="h-3 w-16 bg-gray-800/60 rounded" />
        </div>
        <div className="h-6 w-18 bg-gray-800 rounded" />
      </div>
      <div className="h-7 w-28 bg-gray-800 rounded mb-2" />
      <div className="flex justify-between">
        <div className="h-3 w-20 bg-gray-800/60 rounded" />
        <div className="h-3 w-20 bg-gray-800/60 rounded" />
      </div>
    </div>
  );
}

/** Filter market data by search query (matches ticker or Chinese name) */
function filterBySearch(data: MarketData[], query: string): MarketData[] {
  if (!query.trim()) return data;
  const q = query.trim().toLowerCase();
  return data.filter(
    (m) =>
      m.asset.toLowerCase().includes(q) ||
      (m.nameCn && m.nameCn.includes(q))
  );
}

export default function Home() {
  const [tab, setTab] = useState<TabId>("overview");
  const [searchQuery, setSearchQuery] = useState("");

  const [usData, setUsData] = useState<MarketData[]>(US_TICKERS);
  const [cnData, setCnData] = useState<MarketData[]>(CN_TICKERS);
  const [cryptoData, setCryptoData] = useState<MarketData[]>(CRYPTO_TICKERS);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function fetchAll() {
      setLoading(true);

      const fetchers = [
        fetch("/api/prices?market=us")
          .then((r) => r.json())
          .catch(() => US_TICKERS),
        fetch("/api/prices?market=cn")
          .then((r) => r.json())
          .catch(() => CN_TICKERS),
        fetch("/api/prices?market=crypto")
          .then((r) => r.json())
          .catch(() => CRYPTO_TICKERS),
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

  // Apply search filter
  const filteredUs = useMemo(() => filterBySearch(usData, searchQuery), [usData, searchQuery]);
  const filteredCn = useMemo(() => filterBySearch(cnData, searchQuery), [cnData, searchQuery]);
  const filteredCrypto = useMemo(() => filterBySearch(cryptoData, searchQuery), [cryptoData, searchQuery]);

  const renderCards = (data: MarketData[]) => {
    if (data.length === 0) {
      return (
        <p className="text-xs text-gray-600 py-4">
          No tickers match &quot;{searchQuery}&quot;
        </p>
      );
    }
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {data.map((m) => (
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
      <Header
        tab={tab}
        setTab={setTab}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
      />

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {tab === "overview" && (
          <div className="space-y-8">
            {/* US Equities */}
            <section>
              <h2 className="text-lg font-semibold mb-4 text-gray-300">
                US Equities
              </h2>
              {loading ? renderSkeletons(6) : renderCards(filteredUs)}
            </section>

            {/* Cryptocurrency */}
            <section>
              <h2 className="text-lg font-semibold mb-4 text-gray-300">
                Cryptocurrency
              </h2>
              {loading ? renderSkeletons(3) : renderCards(filteredCrypto)}
            </section>

            {/* China A-Shares */}
            <section>
              <h2 className="text-lg font-semibold mb-4 text-gray-300">
                China A-Shares
              </h2>
              {loading ? renderSkeletons(6) : renderCards(filteredCn)}
            </section>

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
            FinClaw &middot; Open-source quantitative research platform
          </p>
        </div>
      </footer>
    </div>
  );
}
