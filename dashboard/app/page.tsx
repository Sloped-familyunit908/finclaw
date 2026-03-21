"use client";

import { useState } from "react";
import type { TabId } from "@/app/types";

import Header from "@/app/components/Header";
import BacktestTable from "@/app/components/BacktestTable";
import CNScanner from "@/app/components/CNScanner";
import MarketIndexBanner from "@/app/components/MarketIndexBanner";
import FeaturedCards from "@/app/components/FeaturedCards";
import WatchlistTable from "@/app/components/WatchlistTable";
import EvolutionStatus from "@/app/components/EvolutionStatus";
import TopMovers from "@/app/components/TopMovers";
import NewsPanel from "@/app/components/NewsPanel";
import SectorHeatmap from "@/app/components/SectorHeatmap";
import EconomicCalendar from "@/app/components/EconomicCalendar";

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
          <>
            {/* Featured Ticker Cards — full width */}
            <FeaturedCards />

            {/* Two-column layout */}
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
              {/* Left Column (60%) */}
              <div className="lg:col-span-3 space-y-6">
                <SectorHeatmap />
                <WatchlistTable />
              </div>

              {/* Right Column (40%) */}
              <div className="lg:col-span-2 space-y-4">
                <EvolutionStatus />
                <EconomicCalendar />
                <TopMovers />
                <NewsPanel ticker="market" maxItems={5} compact />
              </div>
            </div>
          </>
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
