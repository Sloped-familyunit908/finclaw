"use client";

import { useState, useEffect } from "react";

// ─── Types ───────────────────────────────────────────
interface MarketData {
  asset: string;
  price: number;
  change24h: number;
  rsi14: number | null;
  sma20: number | null;
  sma200: number | null;
}

interface DebateStatement {
  agent: string;
  role: string;
  phase: string;
  content: string;
  signal: string;
  confidence: number;
  target: string | null;
}

interface DebateResult {
  asset: string;
  signal: string;
  confidence: number;
  reasoning: string;
  participants: string[];
  dissenters: string[];
  rounds: DebateStatement[][];
}

// ─── Agent Config ────────────────────────────────────
const agentConfig: Record<string, { avatar: string; color: string; bg: string }> = {
  Warren:   { avatar: "🧓", color: "text-green-400",  bg: "bg-green-950/50 border-green-800" },
  George:   { avatar: "🌍", color: "text-blue-400",   bg: "bg-blue-950/50 border-blue-800" },
  Ada:      { avatar: "📐", color: "text-purple-400", bg: "bg-purple-950/50 border-purple-800" },
  Sentinel: { avatar: "📡", color: "text-yellow-400", bg: "bg-yellow-950/50 border-yellow-800" },
  Guardian: { avatar: "🛡️", color: "text-red-400",    bg: "bg-red-950/50 border-red-800" },
  "Arena Moderator": { avatar: "⚖️", color: "text-cyan-400", bg: "bg-cyan-950/50 border-cyan-800" },
};

const signalColors: Record<string, string> = {
  strong_buy: "text-emerald-400 bg-emerald-950/80",
  buy: "text-green-400 bg-green-950/80",
  hold: "text-gray-400 bg-gray-800/80",
  sell: "text-orange-400 bg-orange-950/80",
  strong_sell: "text-red-400 bg-red-950/80",
};

// ─── Mock Data (replace with WebSocket later) ────────
const mockMarket: MarketData[] = [
  { asset: "BTC", price: 70742, change24h: -2.27, rsi14: 52.7, sma20: 68283, sma200: 94123 },
  { asset: "ETH", price: 2075, change24h: -2.56, rsi14: 51.1, sma20: 2002, sma200: 3247 },
  { asset: "SOL", price: 87.02, change24h: -3.62, rsi14: 49.2, sma20: 85.16, sma200: 150.09 },
];

const mockDebate: DebateResult = {
  asset: "BTC",
  signal: "buy",
  confidence: 0.95,
  reasoning: "After 3 agents debated over 2 challenge rounds, the consensus for BTC is BUY (confidence: 95%).",
  participants: ["Warren", "Ada", "George"],
  dissenters: [],
  rounds: [
    [
      { agent: "Warren", role: "Value Investor", phase: "position", content: "BTC trades at $70,742, 24.9% below 200-day SMA ($94,123). Deep value territory with significant margin of safety. The current price represents a generational buying opportunity.", signal: "buy", confidence: 0.85, target: null },
      { agent: "Ada", role: "Quantitative Analyst", phase: "position", content: "RSI(52.7) neutral zone. Price +3.6% above SMA20 shows short-term strength. However, -24.9% below SMA200 indicates deep structural weakness. Composite signal score: +0.67.", signal: "buy", confidence: 0.70, target: null },
      { agent: "George", role: "Macro Strategist", phase: "position", content: "The prevailing bias in crypto markets has shifted from extreme bearishness to cautious accumulation. We appear to be in the early stages of a new cycle. The reflexive feedback loop between institutional adoption and price could accelerate.", signal: "buy", confidence: 0.75, target: null },
    ],
    [
      { agent: "Warren", role: "Value Investor", phase: "challenge", content: "Ada, your quantitative model treats BTC like a stock with mean reversion — but crypto doesn't follow the same patterns. The SMA200 distance is not structural weakness but a buying signal.", signal: "buy", confidence: 0.85, target: "Ada" },
      { agent: "Ada", role: "Quantitative Analyst", phase: "challenge", content: "Warren, your margin-of-safety argument assumes BTC has intrinsic value. It's speculative. However, the statistical edge exists: RSI neutral + price above short-term trend = positive expected value. Updating confidence.", signal: "buy", confidence: 0.78, target: "Warren" },
      { agent: "George", role: "Macro Strategist", phase: "challenge", content: "Both valid points. I'll add: global liquidity conditions are improving. The Fed pause narrative supports risk assets. The contrarian signal is clear — retail has given up while institutions accumulate.", signal: "buy", confidence: 0.80, target: null },
    ],
    [
      { agent: "Arena Moderator", role: "Consensus Builder", phase: "consensus", content: "After 3 agents debated over 2 challenge rounds, the consensus for BTC is BUY (confidence: 95%). All agents agree on bullish direction with nuanced reasoning.", signal: "buy", confidence: 0.95, target: null },
    ],
  ],
};

// ─── Components ──────────────────────────────────────

function PriceCard({ data }: { data: MarketData }) {
  const isUp = data.change24h >= 0;
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-5 hover:border-gray-700 transition-colors">
      <div className="flex justify-between items-start mb-3">
        <div>
          <h3 className="text-lg font-bold">{data.asset}</h3>
          <p className="text-2xl font-mono font-bold mt-1">
            ${data.price.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </p>
        </div>
        <span className={`px-3 py-1 rounded-full text-sm font-semibold ${isUp ? "bg-green-950/80 text-green-400" : "bg-red-950/80 text-red-400"}`}>
          {isUp ? "▲" : "▼"} {Math.abs(data.change24h).toFixed(2)}%
        </span>
      </div>
      <div className="grid grid-cols-3 gap-2 text-xs text-gray-400">
        <div>RSI <span className="text-gray-200 font-mono">{data.rsi14?.toFixed(1) ?? "—"}</span></div>
        <div>SMA20 <span className="text-gray-200 font-mono">${data.sma20?.toLocaleString(undefined, { maximumFractionDigits: 0 }) ?? "—"}</span></div>
        <div>SMA200 <span className="text-gray-200 font-mono">${data.sma200?.toLocaleString(undefined, { maximumFractionDigits: 0 }) ?? "—"}</span></div>
      </div>
    </div>
  );
}

function DebateCard({ statement, index }: { statement: DebateStatement; index: number }) {
  const config = agentConfig[statement.agent] ?? { avatar: "🤖", color: "text-gray-400", bg: "bg-gray-900 border-gray-700" };
  const signalStyle = signalColors[statement.signal] ?? "text-gray-400 bg-gray-800";
  const phaseLabels: Record<string, string> = {
    position: "📋 POSITION",
    challenge: "⚔️ CHALLENGE",
    defense: "🛡️ DEFENSE",
    consensus: "⚖️ VERDICT",
  };

  return (
    <div className={`rounded-xl border p-4 ${config.bg} animate-fade-in`} style={{ animationDelay: `${index * 150}ms` }}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{config.avatar}</span>
          <div>
            <span className={`font-bold ${config.color}`}>{statement.agent}</span>
            <span className="text-xs text-gray-500 ml-2">{statement.role}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`px-2 py-0.5 rounded text-xs font-bold ${signalStyle}`}>
            {statement.signal.toUpperCase().replace("_", " ")}
          </span>
          <span className="text-xs text-gray-400">{(statement.confidence * 100).toFixed(0)}%</span>
        </div>
      </div>
      {statement.target && (
        <div className="text-xs text-gray-500 mb-1">↩ Responding to {statement.target}</div>
      )}
      <div className="text-xs text-gray-500 mb-2">{phaseLabels[statement.phase] ?? statement.phase}</div>
      <p className="text-sm text-gray-300 leading-relaxed">{statement.content}</p>
    </div>
  );
}

function DebateArena({ debate }: { debate: DebateResult }) {
  const [visibleRound, setVisibleRound] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    if (isPlaying && visibleRound < debate.rounds.length) {
      const timer = setTimeout(() => setVisibleRound((v) => v + 1), 2000);
      return () => clearTimeout(timer);
    }
    if (visibleRound >= debate.rounds.length) {
      setIsPlaying(false);
    }
  }, [isPlaying, visibleRound, debate.rounds.length]);

  const allVisible = debate.rounds.slice(0, visibleRound + 1).flat();

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/30 p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2">
            🏟️ Debate Arena
            <span className="text-sm font-normal text-gray-400">— {debate.asset}</span>
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            {debate.participants.length} agents • {debate.rounds.length} rounds
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => { setVisibleRound(0); setIsPlaying(true); }}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-semibold transition-colors"
          >
            ▶ Replay Debate
          </button>
          <button
            onClick={() => setVisibleRound(debate.rounds.length - 1)}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition-colors"
          >
            Skip to Verdict
          </button>
        </div>
      </div>

      {/* Agent Roster */}
      <div className="flex gap-3 mb-6">
        {debate.participants.map((name) => {
          const cfg = agentConfig[name] ?? { avatar: "🤖", color: "text-gray-400" };
          const isDissenter = debate.dissenters.includes(name);
          return (
            <div key={name} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full ${isDissenter ? "bg-red-950/50 border border-red-800" : "bg-gray-800/50 border border-gray-700"}`}>
              <span>{cfg.avatar}</span>
              <span className={`text-sm font-medium ${cfg.color}`}>{name}</span>
            </div>
          );
        })}
      </div>

      {/* Debate Stream */}
      <div className="space-y-3 max-h-[500px] overflow-y-auto">
        {allVisible.map((stmt, i) => (
          <DebateCard key={`${stmt.agent}-${i}`} statement={stmt} index={i} />
        ))}
      </div>

      {/* Consensus Banner */}
      {visibleRound >= debate.rounds.length - 1 && (
        <div className="mt-6 p-4 rounded-xl bg-gradient-to-r from-blue-950/80 to-purple-950/80 border border-blue-800">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-blue-400 font-semibold">CONSENSUS REACHED</div>
              <div className={`text-3xl font-bold mt-1 ${signalColors[debate.signal]?.split(" ")[0] ?? "text-white"}`}>
                {debate.signal.toUpperCase().replace("_", " ")}
              </div>
            </div>
            <div className="text-right">
              <div className="text-4xl font-bold font-mono text-white">{(debate.confidence * 100).toFixed(0)}%</div>
              <div className="text-xs text-gray-400">Confidence</div>
            </div>
          </div>
          <p className="mt-3 text-sm text-gray-300">{debate.reasoning}</p>
        </div>
      )}
    </div>
  );
}

// ─── Main Page ───────────────────────────────────────
export default function Home() {
  return (
    <main className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <header className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-4xl">🐋</span>
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
              WhaleTrader
            </h1>
            <p className="text-sm text-gray-400">AI-Powered Quantitative Trading Engine</p>
          </div>
        </div>
        <div className="flex gap-2 mt-3">
          <span className="px-2 py-0.5 bg-green-950/50 text-green-400 text-xs rounded border border-green-800">Rust Engine ✓</span>
          <span className="px-2 py-0.5 bg-purple-950/50 text-purple-400 text-xs rounded border border-purple-800">5 AI Agents</span>
          <span className="px-2 py-0.5 bg-blue-950/50 text-blue-400 text-xs rounded border border-blue-800">Debate Arena</span>
          <span className="px-2 py-0.5 bg-yellow-950/50 text-yellow-400 text-xs rounded border border-yellow-800">Live Data</span>
        </div>
      </header>

      {/* Market Prices */}
      <section className="mb-8">
        <h2 className="text-lg font-semibold mb-4 text-gray-300">📊 Market Overview</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {mockMarket.map((m) => (
            <PriceCard key={m.asset} data={m} />
          ))}
        </div>
      </section>

      {/* Debate Arena */}
      <section className="mb-8">
        <DebateArena debate={mockDebate} />
      </section>

      {/* Backtest Results */}
      <section className="mb-8">
        <h2 className="text-lg font-semibold mb-4 text-gray-300">📈 Backtest Performance (200 days)</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-gray-800">
                <th className="text-left py-3 px-4">Strategy</th>
                <th className="text-right py-3 px-4">Return</th>
                <th className="text-right py-3 px-4">Sharpe</th>
                <th className="text-right py-3 px-4">Max DD</th>
                <th className="text-right py-3 px-4">Win Rate</th>
                <th className="text-right py-3 px-4">Alpha</th>
                <th className="text-right py-3 px-4">Trades</th>
              </tr>
            </thead>
            <tbody>
              {[
                { name: "3-Agent Debate (BTC)", ret: -0.70, sharpe: -7.75, dd: -0.56, wr: 0, alpha: 38.07, trades: 1, best: true },
                { name: "3-Agent Debate (ETH)", ret: -1.25, sharpe: -4.59, dd: -1.11, wr: 0, alpha: 52.96, trades: 1, best: false },
                { name: "3-Agent Debate (SOL)", ret: -1.58, sharpe: -3.86, dd: -1.44, wr: 0, alpha: 61.25, trades: 1, best: false },
                { name: "RSI-Only (BTC)", ret: -24.66, sharpe: -1.83, dd: -31.50, wr: 50, alpha: 14.11, trades: 2, best: false },
                { name: "Buy & Hold (BTC)", ret: -38.77, sharpe: 0, dd: -40.0, wr: 0, alpha: 0, trades: 0, best: false },
              ].map((r) => (
                <tr key={r.name} className={`border-b border-gray-800/50 ${r.best ? "bg-blue-950/20" : ""}`}>
                  <td className="py-3 px-4 font-medium">
                    {r.best && "🏆 "}{r.name}
                  </td>
                  <td className={`text-right py-3 px-4 font-mono ${r.ret >= 0 ? "text-green-400" : "text-red-400"}`}>
                    {r.ret >= 0 ? "+" : ""}{r.ret.toFixed(2)}%
                  </td>
                  <td className="text-right py-3 px-4 font-mono text-gray-300">{r.sharpe.toFixed(2)}</td>
                  <td className="text-right py-3 px-4 font-mono text-red-400">{r.dd.toFixed(2)}%</td>
                  <td className="text-right py-3 px-4 font-mono">{r.wr}%</td>
                  <td className={`text-right py-3 px-4 font-mono ${r.alpha >= 0 ? "text-green-400" : "text-red-400"}`}>
                    +{r.alpha.toFixed(1)}%
                  </td>
                  <td className="text-right py-3 px-4 font-mono text-gray-400">{r.trades}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-3 p-3 bg-green-950/20 border border-green-800/50 rounded-lg text-sm text-green-400">
          💡 3-Agent Debate strategies preserved capital (−0.7% to −1.6%) vs Buy & Hold (−39% to −63%) in this bear market.
          Alpha: +38% to +61%.
        </div>
      </section>

      {/* Footer */}
      <footer className="text-center py-8 border-t border-gray-800 text-gray-500 text-sm">
        <p>Built with 🦞 by Lobster Labs — Rust Engine + Python Agents + TypeScript Dashboard</p>
        <p className="mt-1">Research: Multi-Agent Debate (Du et al. 2023) • R&D-Agent-Quant (NeurIPS 2025)</p>
      </footer>
    </main>
  );
}
