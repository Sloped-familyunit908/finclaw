"use client";

import { useState } from "react";
import type { TabId } from "@/app/types";

import Header from "@/app/components/Header";
import BacktestTable from "@/app/components/BacktestTable";
import CNScanner from "@/app/components/CNScanner";
import MarketIndexBanner from "@/app/components/MarketIndexBanner";
import WatchlistTable from "@/app/components/WatchlistTable";
import TopMovers from "@/app/components/TopMovers";

export default function Home() {
  const [tab, setTab] = useState<TabId>("overview");

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-gray-100">
      <Header tab={tab} setTab={setTab} />

      {/* Market Index Banner */}
      {tab === "overview" && <MarketIndexBanner />}

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {tab === "overview" && (
          <div className="space-y-8">
            {/* Watchlist — main content */}
            <WatchlistTable />

            {/* Top Movers — below watchlist */}
            <TopMovers />
          </div>
        )}
        {tab === "backtest" && <BacktestTable />}
        {tab === "cn-scanner" && <CNScanner />}
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
