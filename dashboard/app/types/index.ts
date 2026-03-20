/* ════════════════════════════════════════════════════════════════
   TYPE DEFINITIONS — FinClaw 🦀📈
   ════════════════════════════════════════════════════════════════ */

export interface MarketData {
  asset: string;
  price: number;
  change24h: number;
  rsi14: number | null;
  sma20: number | null;
  sma50: number | null;
  sma200: number | null;
  volume24h: number | null;
  marketCap: number | null;
  /** Optional: exchange market (e.g. "US", "CN") */
  market?: string;
  /** Optional: Chinese name for A-share stocks */
  nameCn?: string;
}

export interface AgentReputation {
  name: string;
  avatar: string;
  elo: number;
  accuracy: number;
  totalPredictions: number;
  correctPredictions: number;
  debateWeight: number;
  specialty: string;
}

export interface DebateStatement {
  agent: string;
  role: string;
  phase: string;
  content: string;
  signal: string;
  confidence: number;
  target: string | null;
}

export interface DebateResult {
  asset: string;
  signal: string;
  confidence: number;
  reasoning: string;
  participants: string[];
  dissenters: string[];
  rounds: DebateStatement[][];
}

export interface BacktestResult {
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

export interface RiskConstitution {
  maxPositionPct: number;
  maxDrawdownHalt: number;
  maxDailyLoss: number;
  minDebateConfidence: number;
  minAgentsAgreeing: number;
  maxLeverage: number;
}

export interface CNScannerResult {
  code: string;
  name: string;
  price: number;
  changePct: number;
  volume: string;
  pe: number | null;
  sector: string;
  signal: string;
  score: number;
}

export type TabId = "overview" | "arena" | "backtest" | "strategies" | "agents" | "risk" | "cn-scanner";
