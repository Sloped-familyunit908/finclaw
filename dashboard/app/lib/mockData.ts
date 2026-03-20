/* ════════════════════════════════════════════════════════════════
   MOCK DATA — FinClaw 🦀📈
   Will be replaced by API / WebSocket in production
   ════════════════════════════════════════════════════════════════ */

import type {
  MarketData,
  AgentReputation,
  DebateResult,
  BacktestResult,
  RiskConstitution,
  CNScannerResult,
} from "@/app/types";

/* ── US Stocks market data ── */
export const US_MARKET_DATA: MarketData[] = [
  { asset: "AAPL", price: 178.72, change24h: 1.35, rsi14: 58.4, sma20: 174.50, sma50: 171.20, sma200: 182.30, volume24h: 52.1e6, marketCap: 2.78e12, market: "US" },
  { asset: "NVDA", price: 875.30, change24h: 3.82, rsi14: 68.9, sma20: 830.00, sma50: 780.50, sma200: 620.40, volume24h: 45.7e6, marketCap: 2.15e12, market: "US" },
  { asset: "TSLA", price: 175.20, change24h: -1.45, rsi14: 42.3, sma20: 180.60, sma50: 195.30, sma200: 215.80, volume24h: 98.3e6, marketCap: 557e9, market: "US" },
  { asset: "MSFT", price: 425.80, change24h: 0.92, rsi14: 55.6, sma20: 420.10, sma50: 415.30, sma200: 395.70, volume24h: 22.4e6, marketCap: 3.16e12, market: "US" },
  { asset: "AMZN", price: 186.40, change24h: 2.15, rsi14: 61.2, sma20: 180.30, sma50: 178.90, sma200: 165.50, volume24h: 38.6e6, marketCap: 1.94e12, market: "US" },
  { asset: "META", price: 515.60, change24h: 1.78, rsi14: 63.5, sma20: 500.20, sma50: 485.70, sma200: 420.30, volume24h: 15.2e6, marketCap: 1.32e12, market: "US" },
];

/* ── Crypto market data ── */
export const MARKET_DATA: MarketData[] = [
  { asset: "BTC", price: 70742, change24h: -2.27, rsi14: 52.7, sma20: 68283, sma50: 71717, sma200: 94123, volume24h: 50.4e9, marketCap: 1.41e12, market: "Crypto" },
  { asset: "ETH", price: 2075, change24h: -2.56, rsi14: 51.1, sma20: 2002, sma50: 2150, sma200: 3247, volume24h: 18.2e9, marketCap: 250e9, market: "Crypto" },
  { asset: "SOL", price: 87.02, change24h: -3.62, rsi14: 49.2, sma20: 85.16, sma50: 92.5, sma200: 150.09, volume24h: 4.1e9, marketCap: 42e9, market: "Crypto" },
];

/* ── A-share market data ── */
export const CN_MARKET_DATA: MarketData[] = [
  {
    asset: "600438.SH", nameCn: "通威股份", price: 25.68, change24h: 2.15,
    rsi14: 58.3, sma20: 24.50, sma50: 23.80, sma200: 28.10,
    volume24h: 3.2e9, marketCap: 115.6e9, market: "A股",
  },
  {
    asset: "000988.SZ", nameCn: "华工科技", price: 32.45, change24h: -1.32,
    rsi14: 44.7, sma20: 33.10, sma50: 34.50, sma200: 36.20,
    volume24h: 1.1e9, marketCap: 32.5e9, market: "A股",
  },
  {
    asset: "002415.SZ", nameCn: "海康威视", price: 35.12, change24h: 0.85,
    rsi14: 55.2, sma20: 34.20, sma50: 33.80, sma200: 37.50,
    volume24h: 4.5e9, marketCap: 328e9, market: "A股",
  },
  {
    asset: "300750.SZ", nameCn: "宁德时代", price: 218.50, change24h: -0.45,
    rsi14: 47.8, sma20: 220.30, sma50: 225.60, sma200: 195.40,
    volume24h: 8.9e9, marketCap: 964e9, market: "A股",
  },
  {
    asset: "600519.SH", nameCn: "贵州茅台", price: 1528.00, change24h: 0.32,
    rsi14: 52.1, sma20: 1510.00, sma50: 1495.00, sma200: 1580.00,
    volume24h: 3.8e9, marketCap: 1.92e12, market: "A股",
  },
  {
    asset: "000625.SZ", nameCn: "长安汽车", price: 14.85, change24h: 3.42,
    rsi14: 65.8, sma20: 13.90, sma50: 13.20, sma200: 14.50,
    volume24h: 5.6e9, marketCap: 147e9, market: "A股",
  },
];

/* ── Agent reputations ── */
export const AGENT_REPUTATIONS: AgentReputation[] = [
  { name: "George", avatar: "🌍", elo: 1321, accuracy: 1.0, totalPredictions: 9, correctPredictions: 9, debateWeight: 0.77, specialty: "Macro trends" },
  { name: "Sentinel", avatar: "📡", elo: 1286, accuracy: 1.0, totalPredictions: 6, correctPredictions: 6, debateWeight: 0.70, specialty: "Sentiment" },
  { name: "Guardian", avatar: "🛡️", elo: 1246, accuracy: 1.0, totalPredictions: 3, correctPredictions: 3, debateWeight: 0.61, specialty: "Risk" },
  { name: "Warren", avatar: "🧓", elo: 1112, accuracy: 0.405, totalPredictions: 37, correctPredictions: 15, debateWeight: 0.29, specialty: "Value" },
  { name: "Ada", avatar: "📐", elo: 1112, accuracy: 0.405, totalPredictions: 37, correctPredictions: 15, debateWeight: 0.29, specialty: "Quant" },
];

/* ── Debate result ── */
export const DEBATE: DebateResult = {
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

/* ── Backtest data ── */
export const BACKTEST_DATA: BacktestResult[] = [
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

/* ── Risk constitution ── */
export const RISK: RiskConstitution = {
  maxPositionPct: 0.20,
  maxDrawdownHalt: -0.15,
  maxDailyLoss: -0.05,
  minDebateConfidence: 0.55,
  minAgentsAgreeing: 2,
  maxLeverage: 1.0,
};

/* ── Strategy list ── */
export const STRATEGIES = [
  "golden-cross-momentum", "rsi-mean-reversion", "bollinger-squeeze",
  "multi-timeframe-trend", "volume-profile-breakout", "ai-sentiment-reversal",
  "macd-divergence", "dca-smart", "grid-trading",
];

/* ── CN Scanner mock results ── */
export const CN_SCANNER_RESULTS: CNScannerResult[] = [
  { code: "600438.SH", name: "通威股份", price: 25.68, changePct: 2.15, volume: "12.5万手", pe: 18.3, sector: "光伏", signal: "buy", score: 82 },
  { code: "000625.SZ", name: "长安汽车", price: 14.85, changePct: 3.42, volume: "37.8万手", pe: 22.1, sector: "新能源车", signal: "strong_buy", score: 91 },
  { code: "002415.SZ", name: "海康威视", price: 35.12, changePct: 0.85, volume: "12.8万手", pe: 25.4, sector: "AI安防", signal: "hold", score: 65 },
  { code: "300750.SZ", name: "宁德时代", price: 218.50, changePct: -0.45, volume: "4.1万手", pe: 28.7, sector: "电池", signal: "hold", score: 58 },
  { code: "600519.SH", name: "贵州茅台", price: 1528.00, changePct: 0.32, volume: "1.5万手", pe: 30.2, sector: "白酒", signal: "hold", score: 55 },
  { code: "000988.SZ", name: "华工科技", price: 32.45, changePct: -1.32, volume: "8.2万手", pe: 35.6, sector: "激光", signal: "sell", score: 38 },
  { code: "002594.SZ", name: "比亚迪", price: 312.80, changePct: 1.85, volume: "6.3万手", pe: 24.8, sector: "新能源车", signal: "buy", score: 78 },
  { code: "601318.SH", name: "中国平安", price: 52.30, changePct: -0.57, volume: "15.2万手", pe: 9.8, sector: "金融", signal: "hold", score: 62 },
  { code: "688981.SH", name: "中芯国际", price: 78.90, changePct: 4.21, volume: "9.7万手", pe: null, sector: "半导体", signal: "strong_buy", score: 88 },
  { code: "002475.SZ", name: "立讯精密", price: 38.65, changePct: 1.12, volume: "18.4万手", pe: 32.1, sector: "消费电子", signal: "buy", score: 75 },
];

/* ── Backtest equity curve data (mock) ── */
export const EQUITY_CURVE_DATA = [
  { day: 0, debate3: 100, debate2: 100, buyHold: 100 },
  { day: 20, debate3: 100.5, debate2: 98, buyHold: 95 },
  { day: 40, debate3: 101, debate2: 95, buyHold: 88 },
  { day: 60, debate3: 100.2, debate2: 90, buyHold: 78 },
  { day: 80, debate3: 99.8, debate2: 86, buyHold: 72 },
  { day: 100, debate3: 100.1, debate2: 83, buyHold: 65 },
  { day: 120, debate3: 99.5, debate2: 80, buyHold: 58 },
  { day: 140, debate3: 99.8, debate2: 82, buyHold: 55 },
  { day: 160, debate3: 99.2, debate2: 84, buyHold: 52 },
  { day: 180, debate3: 99.5, debate2: 82, buyHold: 48 },
  { day: 200, debate3: 99.0, debate2: 82, buyHold: 45 },
];
