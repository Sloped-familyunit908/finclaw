"use client";

import { useState, useEffect } from "react";
import type { TabId } from "@/app/types";

function NavTab({ id, label, icon, active, onClick }: {
  id: TabId; label: string; icon: string; active: boolean; onClick: (id: TabId) => void;
}) {
  return (
    <button
      onClick={() => onClick(id)}
      className={`px-3 py-2 text-sm font-medium rounded-lg transition-all whitespace-nowrap ${
        active
          ? "bg-orange-600/20 text-orange-400 border border-orange-700/50"
          : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
      }`}
    >
      <span className="mr-1.5">{icon}</span>{label}
    </button>
  );
}

export default function Header({
  tab,
  setTab,
}: {
  tab: TabId;
  setTab: (id: TabId) => void;
}) {
  const [clock, setClock] = useState("");

  useEffect(() => {
    const tick = () =>
      setClock(new Date().toLocaleTimeString("en-US", { hour12: false }));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  const tabs: { id: TabId; label: string; icon: string }[] = [
    { id: "overview", label: "Overview", icon: "📊" },
    { id: "arena", label: "Arena", icon: "🏟️" },
    { id: "backtest", label: "Backtest", icon: "📈" },
    { id: "cn-scanner", label: "CN Scanner", icon: "🇨🇳" },
    { id: "strategies", label: "Strategies", icon: "📦" },
    { id: "agents", label: "Agents", icon: "🤖" },
    { id: "risk", label: "Risk", icon: "🛡️" },
  ];

  return (
    <header className="border-b border-gray-800/50 bg-[#0a0a0f]/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-3xl">🦀</span>
          <div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-orange-400 via-red-400 to-amber-400 bg-clip-text text-transparent">
              FinClaw
            </h1>
            <p className="text-[10px] text-gray-500 tracking-wider uppercase">
              AI Quantitative Trading Engine 📈
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="hidden md:flex items-center gap-1.5">
            <span className="px-2 py-0.5 bg-orange-950/40 text-orange-400 text-[10px] rounded border border-orange-800/40">
              Python ✓
            </span>
            <span className="px-2 py-0.5 bg-purple-950/40 text-purple-400 text-[10px] rounded border border-purple-800/40">
              5 Agents
            </span>
            <span className="px-2 py-0.5 bg-blue-950/40 text-blue-400 text-[10px] rounded border border-blue-800/40">
              9 Strategies
            </span>
            <span className="px-2 py-0.5 bg-red-950/40 text-red-400 text-[10px] rounded border border-red-800/40">
              12+ Exchanges
            </span>
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
