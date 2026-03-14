"use client";

import { useState, useEffect, useCallback, useMemo } from "react";

/* ════════════════════════════════════════════════════════════════
   TYPE DEFINITIONS
   ════════════════════════════════════════════════════════════════ */

interface MarketData {
  asset: string;
  price: number;
  change24h: number;
  rsi14: number | null;
  sma20: number | null;
  sma50: number | null;
  sma200: number | null;
  volume24h: number | null;
  marketCap: number | null;
}

interface AgentReputation {
  name: string;
  avatar: string;
  elo: number;
  accuracy: number;
  totalPredictions: number;
  correctPredictions: number;
  debateWeight: number;
  specialty: string;
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

interface BacktestResult {
  strategy: string;
  asset: string;
  totalReturn: number;
  alpha: number;
  sharpe: number;
  maxDD: number;
  winRate: number;
  trades: number;
  pValue: number;
  isSignificant: boolean;
  mcProbProfit: number;
  wfEfficiency: number;
  kellyFraction: number;
}

interface RiskConstitution {
  maxPositionPct: number;
  maxDrawdownHalt: number;
  maxDailyLoss: number;
  minDebateConfidence: number;
  minAgentsAgreeing: number;
  maxLeverage: number;
}

/* ════════════════════════════════════════════════════════════════
   AGENT CONFIG
   ════════════════════════════════════════════════════════════════ */

const AGENTS: Record<string, { avatar: string; color: string; bg: string; gradient: string }> = {
  Warren:   { avatar: "🧓", color: "text-green-400",  bg: "bg-green-950/40 border-green-800/60",  gradient: "from-green-600 to-emerald-600" },
  George:   { avatar: "🌍", color: "text-blue-400",   bg: "bg-blue-950/40 border-blue-800/60",    gradient: "from-blue-600 to-cyan-600" },
  Ada:      { avatar: "📐", color: "text-purple-400", bg: "bg-purple-950/40 border-purple-800/60", gradient: "from-purple-600 to-violet-600" },
  Sentinel: { avatar: "📡", color: "text-yellow-400", bg: "bg-yellow-950/40 border-yellow-800/60", gradient: "from-yellow-600 to-amber-600" },
  Guardian: { avatar: "🛡️", color: "text-red-400",    bg: "bg-red-950/40 border-red-800/60",       gradient: "from-red-600 to-rose-600" },
  "Arena Moderator": { avatar: "⚖️", color: "text-cyan-400", bg: "bg-cyan-950/40 border-cyan-800/60", gradient: "from-cyan-600 to-sky-600" },
};

const SIGNAL_STYLES: Record<string, { text: string; bg: string; border: string }> = {
  strong_buy:  { text: "text-emerald-300", bg: "bg-emerald-950/60", border: "border-emerald-700" },
  buy:         { text: "text-green-300",   bg: "bg-green-950/60",   border: "border-green-700" },
  hold:        { text: "text-gray-300",    bg: "bg-gray-800/60",    border: "border-gray-600" },
  sell:        { text: "text-orange-300",  bg: "bg-orange-950/60",  border: "border-orange-700" },
  strong_sell: { text: "text-red-300",     bg: "bg-red-950/60",     border: "border-red-700" },
};

/* ════════════════════════════════════════════════════════════════
   MOCK DATA — will be replaced by API/WebSocket
   ════════════════════════════════════════════════════════════════ */

const MARKET_DATA: MarketData[] = [
  { asset: "BTC", price: 70742, change24h: -2.27, rsi14: 52.7, sma20: 68283, sma50: 71717, sma200: 94123, volume24h: 50.4e9, marketCap: 1.41e12 },
  { asset: "ETH", price: 2075, change24h: -2.56, rsi14: 51.1, sma20: 2002, sma50: 2150, sma200: 3247, volume24h: 18.2e9, marketCap: 250e9 },
  { asset: "SOL", price: 87.02, change24h: -3.62, rsi14: 49.2, sma20: 85.16, sma50: 92.5, sma200: 150.09, volume24h: 4.1e9, marketCap: 42e9 },
];

const AGENT_REPUTATIONS: AgentReputation[] = [
  { name: "George", avatar: "🌍", elo: 1321, accuracy: 1.0, totalPredictions: 9, correctPredictions: 9, debateWeight: 0.77, specialty: "Macro trends" },
  { name: "Sentinel", avatar: "📡", elo: 1286, accuracy: 1.0, totalPredictions: 6, correctPredictions: 6, debateWeight: 0.70, specialty: "Sentiment" },
  { name: "Guardian", avatar: "🛡️", elo: 1246, accuracy: 1.0, totalPredictions: 3, correctPredictions: 3, debateWeight: 0.61, specialty: "Risk" },
  { name: "Warren", avatar: "🧓", elo: 1112, accuracy: 0.405, totalPredictions: 37, correctPredictions: 15, debateWeight: 0.29, specialty: "Value" },
  { name: "Ada", avatar: "📐", elo: 1112, accuracy: 0.405, totalPredictions: 37, correctPredictions: 15, debateWeight: 0.29, specialty: "Quant" },
];

const DEBATE: DebateResult = {
  asset: "BTC",
  signal: "hold",
  confidence: 0.58,
  reasoning: "2-vs-1 HOLD consensus. BTC in consolidation ($68K–$72K). Macro improving but technicals demand patience. Wait for SMA(50) breakout with volume or pullback to $55-60K.",
  participants: ["Warren", "Ada", "George"],
  dissenters: ["George"],
  rounds: [
    [
      { agent: "Warren", role: "Value Investor", phase: "position", content: "BTC at $70,742 trades 25% below SMA(200) — macro downtrend confirmed. No cash flows, no earnings. RSI neutral at 52.7 is noise. I need $50-55K for true margin of safety, or decisive SMA(200) breakout.", signal: "hold", confidence: 0.62, target: null },
      { agent: "Ada", role: "Quantitative Analyst", phase: "position", content: "Price squeezed between SMA(20) $68,283 and SMA(50) $71,717. RSI 52.7 z-score ~0.1 — pure noise. Sharpe estimate 0.35 < 0.5 threshold. Volume $50.4B insufficient for breakout. No measurable statistical edge.", signal: "hold", confidence: 0.62, target: null },
      { agent: "George", role: "Macro Strategist", phase: "position", content: "37% decline from $111K exhibits classic reflexivity. Late-bust to early-stabilization. Fed in cautious easing, global liquidity improving. Asymmetry: 15-20% downside vs 30-40% upside to $90-100K.", signal: "buy", confidence: 0.62, target: null },
    ],
    [
      { agent: "Warren", role: "Value Investor", phase: "challenge", content: "George, where is the margin of safety? You're asking me to catch a falling knife based on reflexivity narrative. Narratives don't produce cash flows.", signal: "hold", confidence: 0.62, target: "George" },
      { agent: "Ada", role: "Quantitative Analyst", phase: "challenge", content: "George, reflexivity is qualitative storytelling, not quantifiable edge. Sharpe 0.35 < 0.5 threshold. SMA(200) divergence of -24.8% correlates with continued downtrend, not reversals.", signal: "hold", confidence: 0.62, target: "George" },
      { agent: "George", role: "Macro Strategist", phase: "defense", content: "Warren, your framework missed BTC's entire 15-year ascent. Ada, your models are backward-looking — reflexive turning points are where statistics break down. The market doesn't wait for your Sharpe to cross 0.5.", signal: "buy", confidence: 0.62, target: null },
    ],
    [
      { agent: "Arena Moderator", role: "Moderator", phase: "consensus", content: "2-vs-1 HOLD. George's macro thesis adds nuance but lacks confirmation. HOLD with alerts: accumulate $55-60K or buy on SMA(50) breakout with 1.5x volume.", signal: "hold", confidence: 0.58, target: null },
    ],
  ],
};

const BACKTEST_DATA: BacktestResult[] = [
  { strategy: "3-Agent Debate", asset: "BTC", totalReturn: -0.01, alpha: 0.3811, sharpe: -9.26, maxDD: -0.0045, winRate: 0, trades: 1, pValue: 0.82, isSignificant: false, mcProbProfit: 0, wfEfficiency: 0, kellyFraction: 0 },
  { strategy: "3-Agent Debate", asset: "ETH", totalReturn: -0.0108, alpha: 0.5304, sharpe: -5.15, maxDD: -0.0094, winRate: 0, trades: 1, pValue: 0.78, isSignificant: false, mcProbProfit: 0, wfEfficiency: 0, kellyFraction: 0 },
  { strategy: "3-Agent Debate", asset: "SOL", totalReturn: -0.014, alpha: 0.6136, sharpe: -4.21, maxDD: -0.0126, winRate: 0, trades: 1, pValue: 0.75, isSignificant: false, mcProbProfit: 0, wfEfficiency: 0, kellyFraction: 0 },
  { strategy: "2-Agent Debate", asset: "BTC", totalReturn: -0.1792, alpha: 0.2078, sharpe: -1.93, maxDD: -0.2162, winRate: 0.182, trades: 11, pValue: 0.12, isSignificant: false, mcProbProfit: 0.18, wfEfficiency: 0.3, kellyFraction: 0.05 },
  { strategy: "2-Agent Debate", asset: "ETH", totalReturn: -0.2728, alpha: 0.2685, sharpe: -1.76, maxDD: -0.3073, winRate: 0.25, trades: 8, pValue: 0.15, isSignificant: false, mcProbProfit: 0.22, wfEfficiency: 0.25, kellyFraction: 0.04 },
  { strategy: "RSI Only", asset: "BTC", totalReturn: -0.2466, alpha: 0.1404, sharpe: -1.83, maxDD: -0.315, winRate: 0.5, trades: 2, pValue: 0.45, isSignificant: false, mcProbProfit: 0.35, wfEfficiency: 0.15, kellyFraction: 0.02 },
  { strategy: "Buy & Hold", asset: "BTC", totalReturn: -0.3877, alpha: 0, sharpe: -1.5, maxDD: -0.40, winRate: 0, trades: 0, pValue: 1, isSignificant: false, mcProbProfit: 0, wfEfficiency: 0, kellyFraction: 0 },
  { strategy: "Buy & Hold", asset: "ETH", totalReturn: -0.5492, alpha: 0, sharpe: -2.1, maxDD: -0.56, winRate: 0, trades: 0, pValue: 1, isSignificant: false, mcProbProfit: 0, wfEfficiency: 0, kellyFraction: 0 },
  { strategy: "Buy & Hold", asset: "SOL", totalReturn: -0.5560, alpha: 0, sharpe: -2.3, maxDD: -0.58, winRate: 0, trades: 0, pValue: 1, isSignificant: false, mcProbProfit: 0, wfEfficiency: 0, kellyFraction: 0 },
];

const RISK: RiskConstitution = {
  maxPositionPct: 0.20,
  maxDrawdownHalt: -0.15,
  maxDailyLoss: -0.05,
  minDebateConfidence: 0.55,
  minAgentsAgreeing: 2,
  maxLeverage: 1.0,
};

const STRATEGIES = [
  "golden-cross-momentum", "rsi-mean-reversion", "bollinger-squeeze",
  "multi-timeframe-trend", "volume-profile-breakout", "ai-sentiment-reversal",
  "macd-divergence", "dca-smart", "grid-trading",
];

/* ════════════════════════════════════════════════════════════════
   UTILITY
   ════════════════════════════════════════════════════════════════ */

const fmt = {
  usd: (n: number, d = 0) => "$" + n.toLocaleString(undefined, { maximumFractionDigits: d }),
  pct: (n: number, d = 2) => (n >= 0 ? "+" : "") + (n * 100).toFixed(d) + "%",
  pctRaw: (n: number, d = 2) => (n >= 0 ? "+" : "") + n.toFixed(d) + "%",
  compact: (n: number) => {
    if (n >= 1e12) return "$" + (n / 1e12).toFixed(2) + "T";
    if (n >= 1e9) return "$" + (n / 1e9).toFixed(1) + "B";
    if (n >= 1e6) return "$" + (n / 1e6).toFixed(1) + "M";
    return "$" + n.toLocaleString();
  },
};

/* ════════════════════════════════════════════════════════════════
   COMPONENTS
   ════════════════════════════════════════════════════════════════ */

type TabId = "overview" | "arena" | "backtest" | "strategies" | "agents" | "risk";

function NavTab({ id, label, icon, active, onClick }: {
  id: TabId; label: string; icon: string; active: boolean; onClick: (id: TabId) => void;
}) {
  return (
    <button
      onClick={() => onClick(id)}
      className={`px-4 py-2 text-sm font-medium rounded-lg transition-all ${
        active
          ? "bg-blue-600/20 text-blue-400 border border-blue-700/50"
          : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
      }`}
    >
      <span className="mr-1.5">{icon}</span>{label}
    </button>
  );
}

function PriceCard({ data }: { data: MarketData }) {
  const isUp = data.change24h >= 0;
  const priceVsSma200 = data.sma200 ? ((data.price - data.sma200) / data.sma200 * 100) : null;
  
  return (
    <div className="group rounded-xl border border-gray-800/60 bg-[#13131a] p-5 hover:border-gray-700/80 transition-all hover:shadow-lg hover:shadow-black/20">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-bold text-gray-100">{data.asset}</h3>
          <p className="text-2xl font-mono font-bold mt-1 text-white">
            {fmt.usd(data.price)}
          </p>
        </div>
        <span className={`px-3 py-1.5 rounded-lg text-sm font-bold ${
          isUp ? "bg-green-950/60 text-green-400 border border-green-800/40" 
               : "bg-red-950/60 text-red-400 border border-red-800/40"
        }`}>
          {isUp ? "▲" : "▼"} {Math.abs(data.change24h).toFixed(2)}%
        </span>
      </div>
      
      <div className="grid grid-cols-2 gap-y-2 gap-x-4 text-xs">
        <div className="flex justify-between">
          <span className="text-gray-500">RSI(14)</span>
          <span className={`font-mono ${
            (data.rsi14 ?? 50) < 30 ? "text-green-400" :
            (data.rsi14 ?? 50) > 70 ? "text-red-400" : "text-gray-300"
          }`}>{data.rsi14?.toFixed(1) ?? "—"}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Volume</span>
          <span className="font-mono text-gray-300">{data.volume24h ? fmt.compact(data.volume24h) : "—"}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">SMA(20)</span>
          <span className="font-mono text-gray-300">{data.sma20 ? fmt.usd(data.sma20) : "—"}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">SMA(50)</span>
          <span className="font-mono text-gray-300">{data.sma50 ? fmt.usd(data.sma50) : "—"}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">SMA(200)</span>
          <span className="font-mono text-gray-300">{data.sma200 ? fmt.usd(data.sma200) : "—"}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">vs SMA200</span>
          <span className={`font-mono ${
            priceVsSma200 !== null && priceVsSma200 < -20 ? "text-red-400" :
            priceVsSma200 !== null && priceVsSma200 > 0 ? "text-green-400" : "text-orange-400"
          }`}>{priceVsSma200 !== null ? fmt.pctRaw(priceVsSma200, 1) : "—"}</span>
        </div>
      </div>
      
      {data.marketCap && (
        <div className="mt-3 pt-3 border-t border-gray-800/50 text-xs text-gray-500">
          Market Cap: {fmt.compact(data.marketCap)}
        </div>
      )}
    </div>
  );
}

function DebateCard({ stmt, idx }: { stmt: DebateStatement; idx: number }) {
  const a = AGENTS[stmt.agent] ?? { avatar: "🤖", color: "text-gray-400", bg: "bg-gray-900 border-gray-700" };
  const s = SIGNAL_STYLES[stmt.signal] ?? SIGNAL_STYLES.hold;
  const phaseIcon: Record<string, string> = { position: "📋", challenge: "⚔️", defense: "🛡️", consensus: "⚖️" };

  return (
    <div className={`rounded-xl border p-4 ${a.bg} transition-all`} style={{ animationDelay: `${idx * 120}ms` }}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-xl">{a.avatar}</span>
          <span className={`font-bold text-sm ${a.color}`}>{stmt.agent}</span>
          <span className="text-[10px] text-gray-500 uppercase tracking-wider">{stmt.role}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${s.text} ${s.bg} border ${s.border}`}>
            {stmt.signal.replace("_", " ")}
          </span>
          <span className="text-xs text-gray-500 font-mono">{(stmt.confidence * 100).toFixed(0)}%</span>
        </div>
      </div>
      {stmt.target && <div className="text-[10px] text-gray-600 mb-1">↩ Responding to {stmt.target}</div>}
      <div className="text-[10px] text-gray-500 mb-1.5">{phaseIcon[stmt.phase] ?? ""} {stmt.phase.toUpperCase()}</div>
      <p className="text-sm text-gray-300 leading-relaxed">{stmt.content}</p>
    </div>
  );
}

function ArenaSection({ debate }: { debate: DebateResult }) {
  const [round, setRound] = useState(0);
  const [playing, setPlaying] = useState(false);
  const allStmts = debate.rounds.slice(0, round + 1).flat();

  useEffect(() => {
    if (playing && round < debate.rounds.length - 1) {
      const t = setTimeout(() => setRound(r => r + 1), 2000);
      return () => clearTimeout(t);
    }
    if (round >= debate.rounds.length - 1) setPlaying(false);
  }, [playing, round, debate.rounds.length]);

  const s = SIGNAL_STYLES[debate.signal] ?? SIGNAL_STYLES.hold;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2">🏟️ Debate Arena <span className="text-sm font-normal text-gray-500">— {debate.asset}</span></h2>
          <p className="text-xs text-gray-500 mt-0.5">{debate.participants.length} agents · {debate.rounds.length} rounds · Real AI debate</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => { setRound(0); setPlaying(true); }} className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-xs font-semibold transition-colors">▶ Replay</button>
          <button onClick={() => setRound(debate.rounds.length - 1)} className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-xs transition-colors">⏭ Verdict</button>
        </div>
      </div>

      <div className="flex gap-2 flex-wrap">
        {debate.participants.map(name => {
          const cfg = AGENTS[name] ?? { avatar: "🤖", color: "text-gray-400" };
          const dissent = debate.dissenters.includes(name);
          return (
            <div key={name} className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-xs ${dissent ? "bg-orange-950/40 border border-orange-800/50" : "bg-gray-800/40 border border-gray-700/50"}`}>
              <span>{cfg.avatar}</span>
              <span className={cfg.color}>{name}</span>
              {dissent && <span className="text-orange-400 text-[10px]">dissent</span>}
            </div>
          );
        })}
      </div>

      <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
        {allStmts.map((s, i) => <DebateCard key={`${s.agent}-${s.phase}-${i}`} stmt={s} idx={i} />)}
      </div>

      {round >= debate.rounds.length - 1 && (
        <div className="p-5 rounded-xl bg-gradient-to-r from-blue-950/50 to-purple-950/50 border border-blue-800/40">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs text-blue-400 font-semibold tracking-wider uppercase">Consensus</div>
              <div className={`text-3xl font-bold mt-1 ${s.text}`}>{debate.signal.toUpperCase().replace("_", " ")}</div>
            </div>
            <div className="text-right">
              <div className="text-4xl font-bold font-mono text-white">{(debate.confidence * 100).toFixed(0)}%</div>
              <div className="text-[10px] text-gray-500 uppercase">Confidence</div>
            </div>
          </div>
          <p className="mt-3 text-sm text-gray-300 leading-relaxed">{debate.reasoning}</p>
        </div>
      )}
    </div>
  );
}

function BacktestTable() {
  const sorted = useMemo(() =>
    [...BACKTEST_DATA].sort((a, b) => b.alpha - a.alpha),
  []);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">📈 Backtest Performance</h2>
        <span className="text-xs text-gray-500">200 days · Bear market · BTC/ETH/SOL</span>
      </div>
      <div className="overflow-x-auto rounded-xl border border-gray-800/60">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-900/50 text-gray-400 text-xs uppercase tracking-wider">
              <th className="text-left py-3 px-4">Strategy</th>
              <th className="text-left py-3 px-3">Asset</th>
              <th className="text-right py-3 px-3">Return</th>
              <th className="text-right py-3 px-3">Alpha</th>
              <th className="text-right py-3 px-3">Sharpe</th>
              <th className="text-right py-3 px-3">Max DD</th>
              <th className="text-right py-3 px-3">Trades</th>
              <th className="text-center py-3 px-3">Sig.</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((r, i) => (
              <tr key={`${r.strategy}-${r.asset}`} className={`border-t border-gray-800/30 ${i === 0 ? "bg-blue-950/10" : "hover:bg-gray-900/30"}`}>
                <td className="py-2.5 px-4 font-medium text-gray-200">{i === 0 && "🏆 "}{r.strategy}</td>
                <td className="py-2.5 px-3 text-gray-400">{r.asset}</td>
                <td className={`py-2.5 px-3 text-right font-mono ${r.totalReturn >= 0 ? "text-green-400" : "text-red-400"}`}>{fmt.pct(r.totalReturn)}</td>
                <td className={`py-2.5 px-3 text-right font-mono ${r.alpha > 0 ? "text-green-400" : "text-gray-400"}`}>{fmt.pct(r.alpha)}</td>
                <td className="py-2.5 px-3 text-right font-mono text-gray-300">{r.sharpe.toFixed(2)}</td>
                <td className="py-2.5 px-3 text-right font-mono text-red-400">{fmt.pct(r.maxDD)}</td>
                <td className="py-2.5 px-3 text-right font-mono text-gray-400">{r.trades}</td>
                <td className="py-2.5 px-3 text-center">{r.isSignificant ? "✅" : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="p-3 bg-green-950/15 border border-green-800/30 rounded-lg text-xs text-green-400">
        💡 3-Agent Debate preserved capital (−1.0% avg) vs Buy & Hold (−50% avg) in a 200-day bear market. Alpha: +38% to +61%.
        Note: Low trade count — needs more data for statistical significance.
      </div>
    </div>
  );
}

function AgentLeaderboard() {
  const eloStars = (elo: number) => "⭐".repeat(Math.min(5, Math.max(1, Math.floor(elo / 260))));

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">🏅 Agent Reputation Leaderboard</h2>
      <div className="grid gap-3">
        {AGENT_REPUTATIONS.map((a, i) => (
          <div key={a.name} className="flex items-center gap-4 p-4 rounded-xl border border-gray-800/50 bg-[#13131a] hover:border-gray-700/60 transition-all">
            <div className="text-2xl w-8 text-center font-bold text-gray-500">#{i + 1}</div>
            <div className="text-3xl">{a.avatar}</div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-bold text-gray-100">{a.name}</span>
                <span className="text-xs text-gray-500">{a.specialty}</span>
              </div>
              <div className="text-xs text-gray-500 mt-0.5">
                {a.correctPredictions}/{a.totalPredictions} correct · Weight {a.debateWeight.toFixed(2)}x
              </div>
            </div>
            <div className="text-right">
              <div className="text-xl font-bold font-mono text-white">{a.elo}</div>
              <div className="text-xs text-gray-500">ELO</div>
            </div>
            <div className="text-right w-20">
              <div className={`text-lg font-bold font-mono ${a.accuracy >= 0.8 ? "text-green-400" : a.accuracy >= 0.5 ? "text-yellow-400" : "text-red-400"}`}>
                {(a.accuracy * 100).toFixed(0)}%
              </div>
              <div className="text-[10px]">{eloStars(a.elo)}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function StrategyGallery() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">📦 Strategy Marketplace</h2>
        <span className="text-xs text-gray-500">{STRATEGIES.length} strategies available</span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {STRATEGIES.map(name => {
          const labels: Record<string, { diff: string; color: string }> = {
            "dca-smart": { diff: "Beginner", color: "text-green-400 bg-green-950/40 border-green-800/40" },
            "rsi-mean-reversion": { diff: "Beginner", color: "text-green-400 bg-green-950/40 border-green-800/40" },
            "golden-cross-momentum": { diff: "Intermediate", color: "text-yellow-400 bg-yellow-950/40 border-yellow-800/40" },
            "bollinger-squeeze": { diff: "Intermediate", color: "text-yellow-400 bg-yellow-950/40 border-yellow-800/40" },
            "macd-divergence": { diff: "Intermediate", color: "text-yellow-400 bg-yellow-950/40 border-yellow-800/40" },
            "grid-trading": { diff: "Intermediate", color: "text-yellow-400 bg-yellow-950/40 border-yellow-800/40" },
            "multi-timeframe-trend": { diff: "Advanced", color: "text-orange-400 bg-orange-950/40 border-orange-800/40" },
            "volume-profile-breakout": { diff: "Advanced", color: "text-orange-400 bg-orange-950/40 border-orange-800/40" },
            "ai-sentiment-reversal": { diff: "Expert", color: "text-red-400 bg-red-950/40 border-red-800/40" },
          };
          const l = labels[name] ?? { diff: "—", color: "text-gray-400 bg-gray-800/40 border-gray-700/40" };
          const displayName = name.split("-").map(w => w[0].toUpperCase() + w.slice(1)).join(" ");
          
          return (
            <div key={name} className="p-4 rounded-xl border border-gray-800/50 bg-[#13131a] hover:border-gray-700/60 transition-all group cursor-pointer">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium text-sm text-gray-200">{displayName}</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-medium border ${l.color}`}>{l.diff}</span>
              </div>
              <div className="text-xs text-gray-500 font-mono">{name}.yaml</div>
              <div className="mt-3 flex gap-1.5">
                <span className="px-2 py-0.5 bg-gray-800/50 text-gray-400 text-[10px] rounded">crypto</span>
                <span className="px-2 py-0.5 bg-gray-800/50 text-gray-400 text-[10px] rounded">YAML</span>
              </div>
              <div className="mt-3 text-xs text-blue-400 opacity-0 group-hover:opacity-100 transition-opacity">
                whale install {name} →
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function RiskPanel() {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">🛡️ Constitutional Risk Framework</h2>
      <p className="text-xs text-gray-500">Immutable rules that CANNOT be overridden by debate consensus. Inspired by Anthropic Constitutional AI.</p>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {[
          { label: "Max Position Size", value: fmt.pct(RISK.maxPositionPct, 0), desc: "Single position limit", icon: "📏" },
          { label: "Drawdown Halt", value: fmt.pct(RISK.maxDrawdownHalt, 0), desc: "Emergency halt trigger", icon: "🛑" },
          { label: "Daily Loss Limit", value: fmt.pct(RISK.maxDailyLoss, 0), desc: "Pause trading for the day", icon: "📉" },
          { label: "Min Confidence", value: fmt.pct(RISK.minDebateConfidence, 0), desc: "Debate must be this confident", icon: "🎯" },
          { label: "Min Agents Agree", value: RISK.minAgentsAgreeing.toString(), desc: "Minimum agents in consensus", icon: "🤝" },
          { label: "Max Leverage", value: RISK.maxLeverage + "x", desc: "No leverage in v1", icon: "⚖️" },
        ].map(r => (
          <div key={r.label} className="p-4 rounded-xl border border-gray-800/50 bg-[#13131a]">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xl">{r.icon}</span>
              <span className="text-sm font-medium text-gray-300">{r.label}</span>
            </div>
            <div className="text-2xl font-bold font-mono text-white">{r.value}</div>
            <div className="text-xs text-gray-500 mt-1">{r.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════
   MAIN PAGE
   ════════════════════════════════════════════════════════════════ */

export default function Home() {
  const [tab, setTab] = useState<TabId>("overview");
  const [clock, setClock] = useState("");

  useEffect(() => {
    const tick = () => setClock(new Date().toLocaleTimeString("en-US", { hour12: false }));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  const tabs: { id: TabId; label: string; icon: string }[] = [
    { id: "overview", label: "Overview", icon: "📊" },
    { id: "arena", label: "Arena", icon: "🏟️" },
    { id: "backtest", label: "Backtest", icon: "📈" },
    { id: "strategies", label: "Strategies", icon: "📦" },
    { id: "agents", label: "Agents", icon: "🤖" },
    { id: "risk", label: "Risk", icon: "🛡️" },
  ];

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800/50 bg-[#0a0a0f]/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-3xl">🐋</span>
            <div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 via-purple-400 to-cyan-400 bg-clip-text text-transparent">
                WhaleTrader
              </h1>
              <p className="text-[10px] text-gray-500 tracking-wider uppercase">AI Quantitative Trading Engine</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="hidden md:flex items-center gap-1.5">
              <span className="px-2 py-0.5 bg-green-950/40 text-green-400 text-[10px] rounded border border-green-800/40">Rust ✓</span>
              <span className="px-2 py-0.5 bg-purple-950/40 text-purple-400 text-[10px] rounded border border-purple-800/40">5 Agents</span>
              <span className="px-2 py-0.5 bg-blue-950/40 text-blue-400 text-[10px] rounded border border-blue-800/40">9 Strategies</span>
            </div>
            <span className="font-mono text-xs text-gray-500">{clock}</span>
          </div>
        </div>
        <div className="max-w-7xl mx-auto px-4 pb-2 flex gap-1 overflow-x-auto">
          {tabs.map(t => <NavTab key={t.id} {...t} active={tab === t.id} onClick={setTab} />)}
        </div>
      </header>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {tab === "overview" && (
          <div className="space-y-8">
            <section>
              <h2 className="text-lg font-semibold mb-4 text-gray-300">Market Overview</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {MARKET_DATA.map(m => <PriceCard key={m.asset} data={m} />)}
              </div>
            </section>
            <ArenaSection debate={DEBATE} />
            <BacktestTable />
          </div>
        )}
        {tab === "arena" && <ArenaSection debate={DEBATE} />}
        {tab === "backtest" && <BacktestTable />}
        {tab === "strategies" && <StrategyGallery />}
        {tab === "agents" && <AgentLeaderboard />}
        {tab === "risk" && <RiskPanel />}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800/30 py-6 mt-12">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <p className="text-xs text-gray-600">Built with 🦞 by Lobster Labs — Rust + Python + TypeScript</p>
          <p className="text-[10px] text-gray-700 mt-1">Research: Multi-Agent Debate (Du et al. 2023) · R&D-Agent-Quant (NeurIPS 2025) · StockAgent (2024)</p>
        </div>
      </footer>
    </div>
  );
}
