/* ════════════════════════════════════════════════════════════════
   API ROUTE — /api/backtest  — FinClaw
   Runs simplified backtests in pure TypeScript
   Accepts strategy config, returns equity curve + metrics + trades
   ════════════════════════════════════════════════════════════════ */

import { NextRequest, NextResponse } from "next/server";
import {
  calcRSI,
  calcMACD,
  calcBollingerBands,
  calcSMA,
} from "@/app/lib/indicators";
import type { HistoryBar } from "@/app/api/history/route";

/* ── Types ── */

interface BacktestRequest {
  strategy: string;
  ticker: string;
  market: string;
  startDate: string;
  endDate: string;
  capital: number;
  params: Record<string, number>;
}

interface Trade {
  date: string;
  action: "BUY" | "SELL";
  price: number;
  shares: number;
  pnl: number | null;
  pnlPct: number | null;
  reason: string;
}

interface EquityPoint {
  date: string;
  value: number;
}

interface BacktestResponse {
  equityCurve: EquityPoint[];
  metrics: {
    totalReturn: number;
    sharpe: number;
    maxDrawdown: number;
    winRate: number;
    totalTrades: number;
    profitFactor: number;
  };
  trades: Trade[];
}

/* ── Compute best range param for the date span ── */
function computeRange(startDate: string, endDate: string): string {
  const start = new Date(startDate);
  const end = new Date(endDate);
  const diffDays = (end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24);
  // Yahoo Finance only returns daily data for ranges up to ~1 year.
  // For longer periods we still use 1y (most recent year of daily data).
  if (diffDays <= 7) return "1w";
  if (diffDays <= 30) return "1m";
  if (diffDays <= 90) return "3m";
  if (diffDays <= 180) return "6m";
  return "1y";
}

/* ── Fetch history data ── */
async function fetchHistory(
  ticker: string,
  range: string,
  baseUrl: string,
): Promise<HistoryBar[]> {
  const url = `${baseUrl}/api/history?code=${encodeURIComponent(ticker)}&range=${range}`;
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`Failed to fetch history for ${ticker}`);
  return resp.json();
}

/* ── Filter bars by date range ── */
function filterByDateRange(
  bars: HistoryBar[],
  startDate: string,
  endDate: string,
): HistoryBar[] {
  return bars.filter((b) => b.date >= startDate && b.date <= endDate);
}

/* ── Strategy Runners ── */

function runRSI(
  bars: HistoryBar[],
  capital: number,
  params: Record<string, number>,
): { trades: Trade[]; equityCurve: EquityPoint[] } {
  const rsiBuy = params.rsiBuy ?? 30;
  const rsiSell = params.rsiSell ?? 70;
  const stopLoss = (params.stopLoss ?? 5) / 100;
  const takeProfit = (params.takeProfit ?? 20) / 100;

  const closes = bars.map((b) => b.close);
  const rsi = calcRSI(closes, 14);

  const trades: Trade[] = [];
  const equityCurve: EquityPoint[] = [];

  let cash = capital;
  let shares = 0;
  let entryPrice = 0;

  for (let i = 0; i < bars.length; i++) {
    const price = bars[i].close;
    const portfolioValue = cash + shares * price;
    equityCurve.push({ date: bars[i].date, value: portfolioValue });

    if (isNaN(rsi[i])) continue;

    // Check stop loss / take profit if in position
    if (shares > 0) {
      const pnlPct = (price - entryPrice) / entryPrice;
      if (pnlPct <= -stopLoss) {
        const pnl = (price - entryPrice) * shares;
        trades.push({
          date: bars[i].date,
          action: "SELL",
          price,
          shares,
          pnl,
          pnlPct,
          reason: `Stop loss (${(pnlPct * 100).toFixed(1)}%)`,
        });
        cash += shares * price;
        shares = 0;
        entryPrice = 0;
        equityCurve[equityCurve.length - 1].value = cash;
        continue;
      }
      if (pnlPct >= takeProfit) {
        const pnl = (price - entryPrice) * shares;
        trades.push({
          date: bars[i].date,
          action: "SELL",
          price,
          shares,
          pnl,
          pnlPct,
          reason: `Take profit (${(pnlPct * 100).toFixed(1)}%)`,
        });
        cash += shares * price;
        shares = 0;
        entryPrice = 0;
        equityCurve[equityCurve.length - 1].value = cash;
        continue;
      }
    }

    // RSI signals
    if (shares === 0 && rsi[i] < rsiBuy) {
      shares = Math.floor(cash / price);
      if (shares > 0) {
        entryPrice = price;
        cash -= shares * price;
        trades.push({
          date: bars[i].date,
          action: "BUY",
          price,
          shares,
          pnl: null,
          pnlPct: null,
          reason: `RSI = ${rsi[i].toFixed(1)} < ${rsiBuy}`,
        });
      }
    } else if (shares > 0 && rsi[i] > rsiSell) {
      const pnl = (price - entryPrice) * shares;
      const pnlPct = (price - entryPrice) / entryPrice;
      trades.push({
        date: bars[i].date,
        action: "SELL",
        price,
        shares,
        pnl,
        pnlPct,
        reason: `RSI = ${rsi[i].toFixed(1)} > ${rsiSell}`,
      });
      cash += shares * price;
      shares = 0;
      entryPrice = 0;
    }
  }

  // Close any open position at the end
  if (shares > 0 && bars.length > 0) {
    const lastBar = bars[bars.length - 1];
    const price = lastBar.close;
    const pnl = (price - entryPrice) * shares;
    const pnlPct = (price - entryPrice) / entryPrice;
    trades.push({
      date: lastBar.date,
      action: "SELL",
      price,
      shares,
      pnl,
      pnlPct,
      reason: "End of period",
    });
    cash += shares * price;
    shares = 0;
    if (equityCurve.length > 0) {
      equityCurve[equityCurve.length - 1].value = cash;
    }
  }

  return { trades, equityCurve };
}

function runMACD(
  bars: HistoryBar[],
  capital: number,
  params: Record<string, number>,
): { trades: Trade[]; equityCurve: EquityPoint[] } {
  const stopLoss = (params.stopLoss ?? 5) / 100;
  const takeProfit = (params.takeProfit ?? 20) / 100;

  const closes = bars.map((b) => b.close);
  const { macd, signal } = calcMACD(closes, 12, 26, 9);

  const trades: Trade[] = [];
  const equityCurve: EquityPoint[] = [];

  let cash = capital;
  let shares = 0;
  let entryPrice = 0;

  for (let i = 1; i < bars.length; i++) {
    const price = bars[i].close;
    const portfolioValue = cash + shares * price;
    equityCurve.push({ date: bars[i].date, value: portfolioValue });

    if (isNaN(macd[i]) || isNaN(signal[i]) || isNaN(macd[i - 1]) || isNaN(signal[i - 1]))
      continue;

    // Stop loss / take profit
    if (shares > 0) {
      const pnlPct = (price - entryPrice) / entryPrice;
      if (pnlPct <= -stopLoss) {
        trades.push({
          date: bars[i].date, action: "SELL", price, shares,
          pnl: (price - entryPrice) * shares, pnlPct,
          reason: `Stop loss (${(pnlPct * 100).toFixed(1)}%)`,
        });
        cash += shares * price;
        shares = 0;
        entryPrice = 0;
        equityCurve[equityCurve.length - 1].value = cash;
        continue;
      }
      if (pnlPct >= takeProfit) {
        trades.push({
          date: bars[i].date, action: "SELL", price, shares,
          pnl: (price - entryPrice) * shares, pnlPct,
          reason: `Take profit (${(pnlPct * 100).toFixed(1)}%)`,
        });
        cash += shares * price;
        shares = 0;
        entryPrice = 0;
        equityCurve[equityCurve.length - 1].value = cash;
        continue;
      }
    }

    // MACD crossover: buy when MACD crosses above signal
    const prevDiff = macd[i - 1] - signal[i - 1];
    const currDiff = macd[i] - signal[i];

    if (shares === 0 && prevDiff <= 0 && currDiff > 0) {
      shares = Math.floor(cash / price);
      if (shares > 0) {
        entryPrice = price;
        cash -= shares * price;
        trades.push({
          date: bars[i].date, action: "BUY", price, shares,
          pnl: null, pnlPct: null,
          reason: "MACD crossed above signal",
        });
      }
    } else if (shares > 0 && prevDiff >= 0 && currDiff < 0) {
      const pnl = (price - entryPrice) * shares;
      const pnlPct = (price - entryPrice) / entryPrice;
      trades.push({
        date: bars[i].date, action: "SELL", price, shares,
        pnl, pnlPct,
        reason: "MACD crossed below signal",
      });
      cash += shares * price;
      shares = 0;
      entryPrice = 0;
    }
  }

  // Close open position
  if (shares > 0 && bars.length > 0) {
    const lastBar = bars[bars.length - 1];
    const price = lastBar.close;
    trades.push({
      date: lastBar.date, action: "SELL", price, shares,
      pnl: (price - entryPrice) * shares,
      pnlPct: (price - entryPrice) / entryPrice,
      reason: "End of period",
    });
    cash += shares * price;
    shares = 0;
    if (equityCurve.length > 0) {
      equityCurve[equityCurve.length - 1].value = cash;
    }
  }

  return { trades, equityCurve };
}

function runBollinger(
  bars: HistoryBar[],
  capital: number,
  params: Record<string, number>,
): { trades: Trade[]; equityCurve: EquityPoint[] } {
  const stopLoss = (params.stopLoss ?? 5) / 100;
  const takeProfit = (params.takeProfit ?? 20) / 100;

  const closes = bars.map((b) => b.close);
  const { upper, lower } = calcBollingerBands(closes, 20, 2);

  const trades: Trade[] = [];
  const equityCurve: EquityPoint[] = [];

  let cash = capital;
  let shares = 0;
  let entryPrice = 0;

  for (let i = 0; i < bars.length; i++) {
    const price = bars[i].close;
    const portfolioValue = cash + shares * price;
    equityCurve.push({ date: bars[i].date, value: portfolioValue });

    if (isNaN(upper[i]) || isNaN(lower[i])) continue;

    // Stop loss / take profit
    if (shares > 0) {
      const pnlPct = (price - entryPrice) / entryPrice;
      if (pnlPct <= -stopLoss) {
        trades.push({
          date: bars[i].date, action: "SELL", price, shares,
          pnl: (price - entryPrice) * shares, pnlPct,
          reason: `Stop loss (${(pnlPct * 100).toFixed(1)}%)`,
        });
        cash += shares * price;
        shares = 0;
        entryPrice = 0;
        equityCurve[equityCurve.length - 1].value = cash;
        continue;
      }
      if (pnlPct >= takeProfit) {
        trades.push({
          date: bars[i].date, action: "SELL", price, shares,
          pnl: (price - entryPrice) * shares, pnlPct,
          reason: `Take profit (${(pnlPct * 100).toFixed(1)}%)`,
        });
        cash += shares * price;
        shares = 0;
        entryPrice = 0;
        equityCurve[equityCurve.length - 1].value = cash;
        continue;
      }
    }

    // Buy when price touches lower band (mean reversion)
    if (shares === 0 && price <= lower[i]) {
      shares = Math.floor(cash / price);
      if (shares > 0) {
        entryPrice = price;
        cash -= shares * price;
        trades.push({
          date: bars[i].date, action: "BUY", price, shares,
          pnl: null, pnlPct: null,
          reason: `Price at lower band ($${lower[i].toFixed(2)})`,
        });
      }
    } else if (shares > 0 && price >= upper[i]) {
      const pnl = (price - entryPrice) * shares;
      const pnlPct = (price - entryPrice) / entryPrice;
      trades.push({
        date: bars[i].date, action: "SELL", price, shares,
        pnl, pnlPct,
        reason: `Price at upper band ($${upper[i].toFixed(2)})`,
      });
      cash += shares * price;
      shares = 0;
      entryPrice = 0;
    }
  }

  // Close open position
  if (shares > 0 && bars.length > 0) {
    const lastBar = bars[bars.length - 1];
    const price = lastBar.close;
    trades.push({
      date: lastBar.date, action: "SELL", price, shares,
      pnl: (price - entryPrice) * shares,
      pnlPct: (price - entryPrice) / entryPrice,
      reason: "End of period",
    });
    cash += shares * price;
    if (equityCurve.length > 0) {
      equityCurve[equityCurve.length - 1].value = cash;
    }
  }

  return { trades, equityCurve };
}

function runGoldenCross(
  bars: HistoryBar[],
  capital: number,
  params: Record<string, number>,
): { trades: Trade[]; equityCurve: EquityPoint[] } {
  const stopLoss = (params.stopLoss ?? 5) / 100;
  const takeProfit = (params.takeProfit ?? 20) / 100;

  const closes = bars.map((b) => b.close);
  const sma50 = calcSMA(closes, 50);
  const sma200 = calcSMA(closes, 200);

  const trades: Trade[] = [];
  const equityCurve: EquityPoint[] = [];

  let cash = capital;
  let shares = 0;
  let entryPrice = 0;

  for (let i = 1; i < bars.length; i++) {
    const price = bars[i].close;
    const portfolioValue = cash + shares * price;
    equityCurve.push({ date: bars[i].date, value: portfolioValue });

    if (isNaN(sma50[i]) || isNaN(sma200[i]) || isNaN(sma50[i - 1]) || isNaN(sma200[i - 1]))
      continue;

    // Stop loss / take profit
    if (shares > 0) {
      const pnlPct = (price - entryPrice) / entryPrice;
      if (pnlPct <= -stopLoss) {
        trades.push({
          date: bars[i].date, action: "SELL", price, shares,
          pnl: (price - entryPrice) * shares, pnlPct,
          reason: `Stop loss (${(pnlPct * 100).toFixed(1)}%)`,
        });
        cash += shares * price;
        shares = 0;
        entryPrice = 0;
        equityCurve[equityCurve.length - 1].value = cash;
        continue;
      }
      if (pnlPct >= takeProfit) {
        trades.push({
          date: bars[i].date, action: "SELL", price, shares,
          pnl: (price - entryPrice) * shares, pnlPct,
          reason: `Take profit (${(pnlPct * 100).toFixed(1)}%)`,
        });
        cash += shares * price;
        shares = 0;
        entryPrice = 0;
        equityCurve[equityCurve.length - 1].value = cash;
        continue;
      }
    }

    // Golden cross: SMA 50 crosses above SMA 200
    if (shares === 0 && sma50[i - 1] <= sma200[i - 1] && sma50[i] > sma200[i]) {
      shares = Math.floor(cash / price);
      if (shares > 0) {
        entryPrice = price;
        cash -= shares * price;
        trades.push({
          date: bars[i].date, action: "BUY", price, shares,
          pnl: null, pnlPct: null,
          reason: "Golden Cross (SMA50 > SMA200)",
        });
      }
    } else if (shares > 0 && sma50[i - 1] >= sma200[i - 1] && sma50[i] < sma200[i]) {
      const pnl = (price - entryPrice) * shares;
      const pnlPct = (price - entryPrice) / entryPrice;
      trades.push({
        date: bars[i].date, action: "SELL", price, shares,
        pnl, pnlPct,
        reason: "Death Cross (SMA50 < SMA200)",
      });
      cash += shares * price;
      shares = 0;
      entryPrice = 0;
    }
  }

  // Close open position
  if (shares > 0 && bars.length > 0) {
    const lastBar = bars[bars.length - 1];
    const price = lastBar.close;
    trades.push({
      date: lastBar.date, action: "SELL", price, shares,
      pnl: (price - entryPrice) * shares,
      pnlPct: (price - entryPrice) / entryPrice,
      reason: "End of period",
    });
    cash += shares * price;
    if (equityCurve.length > 0) {
      equityCurve[equityCurve.length - 1].value = cash;
    }
  }

  return { trades, equityCurve };
}

/* ── Compute metrics from trades and equity curve ── */
function computeMetrics(
  trades: Trade[],
  equityCurve: EquityPoint[],
  initialCapital: number,
) {
  const sellTrades = trades.filter((t) => t.action === "SELL" && t.pnl !== null);
  const wins = sellTrades.filter((t) => (t.pnl ?? 0) > 0);
  const losses = sellTrades.filter((t) => (t.pnl ?? 0) <= 0);

  const finalValue =
    equityCurve.length > 0
      ? equityCurve[equityCurve.length - 1].value
      : initialCapital;
  const totalReturn = (finalValue - initialCapital) / initialCapital;

  // Win rate
  const winRate = sellTrades.length > 0 ? wins.length / sellTrades.length : 0;

  // Profit factor
  const grossProfit = wins.reduce((sum, t) => sum + (t.pnl ?? 0), 0);
  const grossLoss = Math.abs(losses.reduce((sum, t) => sum + (t.pnl ?? 0), 0));
  const profitFactor = grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? Infinity : 0;

  // Max drawdown
  let peak = initialCapital;
  let maxDD = 0;
  for (const pt of equityCurve) {
    if (pt.value > peak) peak = pt.value;
    const dd = (pt.value - peak) / peak;
    if (dd < maxDD) maxDD = dd;
  }

  // Sharpe ratio (annualized, using daily returns)
  let sharpe = 0;
  if (equityCurve.length > 1) {
    const dailyReturns: number[] = [];
    for (let i = 1; i < equityCurve.length; i++) {
      dailyReturns.push(
        (equityCurve[i].value - equityCurve[i - 1].value) /
          equityCurve[i - 1].value,
      );
    }
    const avgReturn =
      dailyReturns.reduce((s, r) => s + r, 0) / dailyReturns.length;
    const variance =
      dailyReturns.reduce((s, r) => s + (r - avgReturn) ** 2, 0) /
      dailyReturns.length;
    const stdDev = Math.sqrt(variance);
    sharpe = stdDev > 0 ? (avgReturn / stdDev) * Math.sqrt(252) : 0;
  }

  return {
    totalReturn,
    sharpe: Math.round(sharpe * 100) / 100,
    maxDrawdown: Math.round(maxDD * 10000) / 10000,
    winRate: Math.round(winRate * 10000) / 10000,
    totalTrades: sellTrades.length,
    profitFactor: Math.round(profitFactor * 100) / 100,
  };
}

/* ── Route handler ── */
export async function POST(request: NextRequest) {
  try {
    const body: BacktestRequest = await request.json();
    const { strategy, ticker, startDate, endDate, capital, params } = body;

    if (!ticker || !strategy) {
      return NextResponse.json(
        { error: "Missing required fields: strategy, ticker" },
        { status: 400 },
      );
    }

    const effectiveCapital = capital || 100_000;

    // Build base URL from the request
    const proto = request.headers.get("x-forwarded-proto") ?? "http";
    const host = request.headers.get("host") ?? "localhost:3000";
    const baseUrl = `${proto}://${host}`;

    // Determine best range parameter for daily data
    const range = computeRange(
      startDate || "2000-01-01",
      endDate || "2099-12-31",
    );

    // Fetch history
    const allBars = await fetchHistory(ticker, range, baseUrl);

    if (!allBars || allBars.length === 0) {
      return NextResponse.json(
        { error: `No history data available for ${ticker}` },
        { status: 404 },
      );
    }

    // Filter by date range
    const bars = filterByDateRange(
      allBars,
      startDate || "2000-01-01",
      endDate || "2099-12-31",
    );

    if (bars.length < 30) {
      return NextResponse.json(
        {
          error: `Insufficient data for ${ticker} in the selected date range (${bars.length} bars, need at least 30)`,
        },
        { status: 400 },
      );
    }

    // Run strategy
    let result: { trades: Trade[]; equityCurve: EquityPoint[] };

    switch (strategy) {
      case "rsi":
        result = runRSI(bars, effectiveCapital, params || {});
        break;
      case "macd":
        result = runMACD(bars, effectiveCapital, params || {});
        break;
      case "bollinger":
        result = runBollinger(bars, effectiveCapital, params || {});
        break;
      case "golden_cross":
        result = runGoldenCross(bars, effectiveCapital, params || {});
        break;
      default:
        return NextResponse.json(
          { error: `Unknown strategy: ${strategy}` },
          { status: 400 },
        );
    }

    // Compute metrics
    const metrics = computeMetrics(
      result.trades,
      result.equityCurve,
      effectiveCapital,
    );

    // Downsample equity curve if too many points (keep it under 500)
    let equityCurve = result.equityCurve;
    if (equityCurve.length > 500) {
      const step = Math.ceil(equityCurve.length / 500);
      const sampled: EquityPoint[] = [];
      for (let i = 0; i < equityCurve.length; i += step) {
        sampled.push(equityCurve[i]);
      }
      // Always include last point
      if (sampled[sampled.length - 1] !== equityCurve[equityCurve.length - 1]) {
        sampled.push(equityCurve[equityCurve.length - 1]);
      }
      equityCurve = sampled;
    }

    const response: BacktestResponse = {
      equityCurve,
      metrics,
      trades: result.trades,
    };

    return NextResponse.json(response);
  } catch (err) {
    return NextResponse.json(
      { error: "Backtest failed", detail: String(err) },
      { status: 500 },
    );
  }
}
