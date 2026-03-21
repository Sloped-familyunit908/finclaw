"use client";

import { useState, useEffect } from "react";
import type { TabId } from "@/app/types";

function NavTab({ id, label, active, onClick }: {
  id: TabId; label: string; active: boolean; onClick: (id: TabId) => void;
}) {
  return (
    <button
      onClick={() => onClick(id)}
      className={`px-3 py-2 text-sm font-medium rounded transition-all whitespace-nowrap ${
        active
          ? "bg-slate-700/40 text-white border border-slate-600/50"
          : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
      }`}
    >
      {label}
    </button>
  );
}

export default function Header({
  tab,
  setTab,
  searchQuery,
  onSearchChange,
}: {
  tab: TabId;
  setTab: (id: TabId) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
}) {
  const [clock, setClock] = useState("");

  useEffect(() => {
    const tick = () =>
      setClock(new Date().toLocaleTimeString("en-US", { hour12: false }));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  // Only show tabs with real content
  const tabs: { id: TabId; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "backtest", label: "Backtest" },
    { id: "cn-scanner", label: "Scanner" },
    { id: "strategies", label: "Strategies" },
  ];

  return (
    <header className="border-b border-gray-800/50 bg-[#0a0a0f]/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">
              FinClaw
            </h1>
            <p className="text-[10px] text-gray-500 tracking-wider uppercase">
              Quantitative Research Platform
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {/* Search input — filters watchlist on overview */}
          <div className="hidden md:flex items-center">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Search ticker..."
              className="w-48 px-3 py-1.5 text-xs bg-gray-900/60 border border-gray-700/50 rounded text-gray-300 placeholder-gray-600 focus:outline-none focus:border-slate-500/60"
            />
          </div>
          <span className="font-mono text-xs text-gray-500">{clock}</span>
        </div>
      </div>
      <div className="max-w-7xl mx-auto px-4 pb-2 flex gap-1 overflow-x-auto scrollbar-hide">
        {tabs.map((t) => (
          <NavTab
            key={t.id}
            {...t}
            active={tab === t.id}
            onClick={setTab}
          />
        ))}
      </div>
    </header>
  );
}
