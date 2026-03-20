"use client";

import { useState, useEffect } from "react";
import type { DebateResult, DebateStatement } from "@/app/types";
import { AGENTS, SIGNAL_STYLES } from "@/app/lib/utils";

function DebateCard({ stmt, idx }: { stmt: DebateStatement; idx: number }) {
  const a = AGENTS[stmt.agent] ?? {
    avatar: "🤖",
    color: "text-gray-400",
    bg: "bg-gray-900 border-gray-700",
  };
  const s = SIGNAL_STYLES[stmt.signal] ?? SIGNAL_STYLES.hold;
  const phaseIcon: Record<string, string> = {
    position: "📋",
    challenge: "⚔️",
    defense: "🛡️",
    consensus: "⚖️",
  };

  return (
    <div
      className={`rounded-xl border p-4 ${a.bg} transition-all`}
      style={{ animationDelay: `${idx * 120}ms` }}
    >
      <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <span className="text-xl">{a.avatar}</span>
          <span className={`font-bold text-sm ${a.color}`}>{stmt.agent}</span>
          <span className="text-[10px] text-gray-500 uppercase tracking-wider hidden sm:inline">
            {stmt.role}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${s.text} ${s.bg} border ${s.border}`}
          >
            {stmt.signal.replace("_", " ")}
          </span>
          <span className="text-xs text-gray-500 font-mono">
            {(stmt.confidence * 100).toFixed(0)}%
          </span>
        </div>
      </div>
      {stmt.target && (
        <div className="text-[10px] text-gray-600 mb-1">
          ↩ Responding to {stmt.target}
        </div>
      )}
      <div className="text-[10px] text-gray-500 mb-1.5">
        {phaseIcon[stmt.phase] ?? ""} {stmt.phase.toUpperCase()}
      </div>
      <p className="text-sm text-gray-300 leading-relaxed">{stmt.content}</p>
    </div>
  );
}

export default function DebateArena({ debate }: { debate: DebateResult }) {
  const [round, setRound] = useState(0);
  const [playing, setPlaying] = useState(false);
  const allStmts = debate.rounds.slice(0, round + 1).flat();

  useEffect(() => {
    if (playing && round < debate.rounds.length - 1) {
      const t = setTimeout(() => setRound((r) => r + 1), 2000);
      return () => clearTimeout(t);
    }
    if (round >= debate.rounds.length - 1) setPlaying(false);
  }, [playing, round, debate.rounds.length]);

  const s = SIGNAL_STYLES[debate.signal] ?? SIGNAL_STYLES.hold;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2">
            🏟️ Debate Arena{" "}
            <span className="text-sm font-normal text-gray-500">
              — {debate.asset}
            </span>
          </h2>
          <p className="text-xs text-gray-500 mt-0.5">
            {debate.participants.length} agents · {debate.rounds.length} rounds ·
            Real AI debate
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => {
              setRound(0);
              setPlaying(true);
            }}
            className="px-3 py-1.5 bg-orange-600 hover:bg-orange-500 rounded-lg text-xs font-semibold transition-colors"
          >
            ▶ Replay
          </button>
          <button
            onClick={() => setRound(debate.rounds.length - 1)}
            className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-xs transition-colors"
          >
            ⏭ Verdict
          </button>
        </div>
      </div>

      <div className="flex gap-2 flex-wrap">
        {debate.participants.map((name) => {
          const cfg = AGENTS[name] ?? {
            avatar: "🤖",
            color: "text-gray-400",
          };
          const dissent = debate.dissenters.includes(name);
          return (
            <div
              key={name}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-xs ${
                dissent
                  ? "bg-orange-950/40 border border-orange-800/50"
                  : "bg-gray-800/40 border border-gray-700/50"
              }`}
            >
              <span>{cfg.avatar}</span>
              <span className={cfg.color}>{name}</span>
              {dissent && (
                <span className="text-orange-400 text-[10px]">dissent</span>
              )}
            </div>
          );
        })}
      </div>

      <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
        {allStmts.map((stmt, i) => (
          <DebateCard
            key={`${stmt.agent}-${stmt.phase}-${i}`}
            stmt={stmt}
            idx={i}
          />
        ))}
      </div>

      {round >= debate.rounds.length - 1 && (
        <div className="p-5 rounded-xl bg-gradient-to-r from-orange-950/30 to-red-950/30 border border-orange-800/40">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs text-orange-400 font-semibold tracking-wider uppercase">
                Consensus
              </div>
              <div className={`text-3xl font-bold mt-1 ${s.text}`}>
                {debate.signal.toUpperCase().replace("_", " ")}
              </div>
            </div>
            <div className="text-right">
              <div className="text-4xl font-bold font-mono text-white">
                {(debate.confidence * 100).toFixed(0)}%
              </div>
              <div className="text-[10px] text-gray-500 uppercase">
                Confidence
              </div>
            </div>
          </div>
          <p className="mt-3 text-sm text-gray-300 leading-relaxed">
            {debate.reasoning}
          </p>
        </div>
      )}
    </div>
  );
}
