"use client";

import { useState, useEffect } from "react";
import type { DebateResult, DebateStatement } from "@/app/types";
import { AGENTS, SIGNAL_STYLES } from "@/app/lib/utils";

function DebateCard({ stmt, idx }: { stmt: DebateStatement; idx: number }) {
  const a = AGENTS[stmt.agent] ?? {
    avatar: "?",
    color: "text-gray-400",
    bg: "bg-gray-900 border-gray-700",
  };
  const s = SIGNAL_STYLES[stmt.signal] ?? SIGNAL_STYLES.hold;
  const phaseLabel: Record<string, string> = {
    position: "POSITION",
    challenge: "CHALLENGE",
    defense: "DEFENSE",
    consensus: "CONSENSUS",
  };

  return (
    <div
      className={`rounded border p-4 ${a.bg} transition-all`}
      style={{ animationDelay: `${idx * 120}ms` }}
    >
      <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <span className={`w-7 h-7 rounded flex items-center justify-center text-xs font-bold bg-gray-800/60 ${a.color}`}>
            {a.avatar}
          </span>
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
          Re: {stmt.target}
        </div>
      )}
      <div className="text-[10px] text-gray-500 mb-1.5 uppercase tracking-wider">
        {phaseLabel[stmt.phase] ?? stmt.phase.toUpperCase()}
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
          <h2 className="text-lg font-semibold text-gray-200">
            Multi-Agent Analysis
            <span className="text-sm font-normal text-gray-500 ml-2">
              {debate.asset}
            </span>
          </h2>
          <p className="text-xs text-gray-500 mt-0.5">
            {debate.participants.length} agents, {debate.rounds.length} rounds
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => {
              setRound(0);
              setPlaying(true);
            }}
            className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded text-xs font-medium transition-colors"
          >
            Replay
          </button>
          <button
            onClick={() => setRound(debate.rounds.length - 1)}
            className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded text-xs transition-colors"
          >
            Skip to Verdict
          </button>
        </div>
      </div>

      <div className="flex gap-2 flex-wrap">
        {debate.participants.map((name) => {
          const cfg = AGENTS[name] ?? {
            avatar: "?",
            color: "text-gray-400",
          };
          const dissent = debate.dissenters.includes(name);
          return (
            <div
              key={name}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs ${
                dissent
                  ? "bg-gray-800/60 border border-gray-600/50"
                  : "bg-gray-800/40 border border-gray-700/50"
              }`}
            >
              <span className={`font-bold ${cfg.color}`}>{cfg.avatar}</span>
              <span className={cfg.color}>{name}</span>
              {dissent && (
                <span className="text-gray-400 text-[10px]">dissent</span>
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
        <div className="p-5 rounded border border-gray-700/50 bg-[#13131a]">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs text-gray-500 font-semibold tracking-wider uppercase">
                Consensus Signal
              </div>
              <div className={`text-2xl font-bold mt-1 ${s.text}`}>
                {debate.signal.toUpperCase().replace("_", " ")}
              </div>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold font-mono text-white">
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
