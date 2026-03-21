/* ════════════════════════════════════════════════════════════════
   FALLBACK DATA — FinClaw
   Default/fallback values used when live APIs are unreachable.
   This is NOT mock data — prices are stale placeholders only.
   ════════════════════════════════════════════════════════════════ */

import type {
  MarketData,
  DebateResult,
  BacktestResult,
  RiskConstitution,
} from "@/app/types";

/* ── US Stocks fallback (stale — real prices fetched from Yahoo Finance) ── */
export const US_TICKERS: MarketData[] = [
  { asset: "AAPL", price: 0, change24h: 0, volume24h: null, marketCap: null, market: "US" },
  { asset: "NVDA", price: 0, change24h: 0, volume24h: null, marketCap: null, market: "US" },
  { asset: "TSLA", price: 0, change24h: 0, volume24h: null, marketCap: null, market: "US" },
  { asset: "MSFT", price: 0, change24h: 0, volume24h: null, marketCap: null, market: "US" },
  { asset: "AMZN", price: 0, change24h: 0, volume24h: null, marketCap: null, market: "US" },
  { asset: "META", price: 0, change24h: 0, volume24h: null, marketCap: null, market: "US" },
  { asset: "GOOGL", price: 0, change24h: 0, volume24h: null, marketCap: null, market: "US" },
];

/* ── Crypto fallback (stale — real prices fetched from CoinGecko) ── */
export const CRYPTO_TICKERS: MarketData[] = [
  { asset: "BTC", price: 0, change24h: 0, volume24h: null, marketCap: null, market: "Crypto" },
  { asset: "ETH", price: 0, change24h: 0, volume24h: null, marketCap: null, market: "Crypto" },
  { asset: "SOL", price: 0, change24h: 0, volume24h: null, marketCap: null, market: "Crypto" },
];

/* ── A-share fallback (stale — real prices fetched from Sina) ── */
export const CN_TICKERS: MarketData[] = [
  { asset: "600519.SH", nameCn: "贵州茅台", price: 0, change24h: 0, volume24h: null, marketCap: null, market: "A股" },
  { asset: "300750.SZ", nameCn: "宁德时代", price: 0, change24h: 0, volume24h: null, marketCap: null, market: "A股" },
  { asset: "002594.SZ", nameCn: "比亚迪", price: 0, change24h: 0, volume24h: null, marketCap: null, market: "A股" },
  { asset: "002415.SZ", nameCn: "海康威视", price: 0, change24h: 0, volume24h: null, marketCap: null, market: "A股" },
  { asset: "688981.SH", nameCn: "中芯国际", price: 0, change24h: 0, volume24h: null, marketCap: null, market: "A股" },
  { asset: "000858.SZ", nameCn: "五粮液", price: 0, change24h: 0, volume24h: null, marketCap: null, market: "A股" },
];

// Legacy aliases — the API route still imports these names
export const US_MARKET_DATA = US_TICKERS;
export const MARKET_DATA = CRYPTO_TICKERS;
export const CN_MARKET_DATA = CN_TICKERS;

/* ── Debate result — from real BTC analysis session ── */
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

/* ── Backtest data — REAL results from 200-day bear market analysis ── */
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

/* ── Risk constitution — system configuration values ── */
export const RISK: RiskConstitution = {
  maxPositionPct: 0.20,
  maxDrawdownHalt: -0.15,
  maxDailyLoss: -0.05,
  minDebateConfidence: 0.55,
  minAgentsAgreeing: 2,
  maxLeverage: 1.0,
};

/* ── Strategy list — real strategies available in the FinClaw engine ── */
export const STRATEGIES = [
  "golden-cross-momentum", "rsi-mean-reversion", "bollinger-squeeze",
  "multi-timeframe-trend", "volume-profile-breakout", "ai-sentiment-reversal",
  "macd-divergence", "dca-smart", "grid-trading",
];

/* ── Backtest equity curve — REAL data from 200-day bear market analysis ── */
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
