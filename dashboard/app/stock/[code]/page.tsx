"use client";

import { useEffect, useState, useMemo, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import type { IChartApi } from "lightweight-charts";
import type { HistoryBar } from "@/app/api/history/route";
import {
  calcRSI,
  calcMACD,
  calcBollingerBands,
  calcSMA,
  calcKDJ,
} from "@/app/lib/indicators";
import { fmt } from "@/app/lib/utils";
import { findTicker } from "@/app/lib/tickers";
import TimeRangeSelector, { type TimeRange } from "@/app/components/TimeRangeSelector";
import FundamentalsPanel from "@/app/components/FundamentalsPanel";
import { SetAlertModal } from "@/app/components/PriceAlerts";

/* -- Helpers -- */
function isCN(code: string) {
  return /\.(SH|SZ)$/i.test(code);
}
function isCrypto(code: string) {
  return ["BTC", "ETH", "SOL"].includes(code.toUpperCase());
}
function fmtP(price: number, cn: boolean) {
  return cn ? fmt.cny(price) : fmt.usd(price);
}
function last<T>(arr: T[]): T | undefined {
  return arr[arr.length - 1];
}
function lastNum(arr: number[]): number {
  for (let i = arr.length - 1; i >= 0; i--) {
    if (!isNaN(arr[i])) return arr[i];
  }
  return NaN;
}

/* -- Technical Analysis Summary -- */
function generateAnalysis(
  code: string,
  name: string,
  price: number,
  rsi: number,
  macdHist: number,
  sma20: number,
  sma50: number,
  cn: boolean,
) {
  const rsiInterp =
    rsi > 70 ? "overbought" : rsi < 30 ? "oversold" : rsi > 60 ? "above-neutral" : rsi < 40 ? "below-neutral" : "neutral";
  const macdSignal = macdHist > 0 ? "bullish" : "bearish";
  const maAbove20 = price > sma20;
  const maAbove50 = price > sma50;

  let score = 5;
  const factors: string[] = [];

  if (rsi > 40 && rsi < 60) { score += 1; factors.push("RSI neutral (+1)"); }
  else if (rsi < 30) { score += 2; factors.push("RSI oversold (+2)"); }
  else if (rsi > 70) { score -= 1; factors.push("RSI overbought (-1)"); }

  if (macdHist > 0) { score += 1; factors.push("MACD bullish (+1)"); }
  else { score -= 1; factors.push("MACD bearish (-1)"); }

  if (maAbove20 && maAbove50) { score += 2; factors.push("MA alignment bullish (+2)"); }
  else if (!maAbove20 && !maAbove50) { score -= 1; factors.push("MA alignment bearish (-1)"); }

  score = Math.max(1, Math.min(10, score));

  const signalText = score >= 7 ? "Bullish" : score <= 3 ? "Bearish" : "Neutral";
  const stopLoss = price * 0.92;
  const currency = cn ? "\u00a5" : "$";

  return {
    score,
    signalText,
    rsiInterp,
    macdSignal,
    factors,
    stopLoss: `${currency}${stopLoss.toFixed(2)}`,
  };
}

/* ================================================================ */
export default function StockDetailPage() {
  const params = useParams();
  const code = decodeURIComponent(params.code as string);
  const cn = isCN(code);
  const crypto = isCrypto(code);

  const [history, setHistory] = useState<HistoryBar[]>([]);
  const [yearHistory, setYearHistory] = useState<HistoryBar[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState<TimeRange>("1m");
  const [watchlistState, setWatchlistState] = useState<"idle" | "added" | "exists">("idle");
  const [showAlertModal, setShowAlertModal] = useState(false);

  const chartContainerRef = useRef<HTMLDivElement>(null);
  const macdChartContainerRef = useRef<HTMLDivElement>(null);

  // Check watchlist on mount
  useEffect(() => {
    try {
      const wl = JSON.parse(localStorage.getItem("finclaw_watchlist") || "[]") as string[];
      if (wl.includes(code)) setWatchlistState("exists");
    } catch { /* ignore */ }
  }, [code]);

  // Fetch history when code or timeRange changes
  useEffect(() => {
    setLoading(true);
    setError(null);

    fetch(`/api/history?code=${encodeURIComponent(code)}&range=${timeRange}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          // De-duplicate by date (API may return duplicate timestamps)
          const seen = new Set<string>();
          const deduped = data.filter((d: { date: string }) => {
            if (seen.has(d.date)) return false;
            seen.add(d.date);
            return true;
          });
          setHistory(deduped);
        } else {
          setError("No data available");
        }
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [code, timeRange]);

  // Fetch 1Y history for 52-week high/low
  useEffect(() => {
    fetch(`/api/history?code=${encodeURIComponent(code)}&range=1y`)
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setYearHistory(data);
        }
      })
      .catch(() => {
        // silent — 52w data is supplementary
      });
  }, [code]);

  // Compute 52-week high/low
  const week52 = useMemo(() => {
    if (yearHistory.length === 0) return null;
    const highs = yearHistory.map((b) => b.high);
    const lows = yearHistory.map((b) => b.low);
    return {
      high: Math.max(...highs),
      low: Math.min(...lows),
    };
  }, [yearHistory]);

  /* -- Compute indicators -- */
  const indicators = useMemo(() => {
    if (history.length < 2) return null;

    const closes = history.map((b) => b.close);
    const highs = history.map((b) => b.high);
    const lows = history.map((b) => b.low);

    const rsi = calcRSI(closes, 14);
    const macd = calcMACD(closes);
    const bb = calcBollingerBands(closes, 20);
    const sma20 = calcSMA(closes, 20);
    const sma50 = calcSMA(closes, 50);
    const kdj = calcKDJ(highs, lows, closes);

    return { rsi, macd, bb, sma20, sma50, kdj, closes, highs, lows };
  }, [history]);

  /* -- TradingView Candlestick Chart -- */
  useEffect(() => {
    if (!chartContainerRef.current || !history.length || !indicators) return;

    let chart: IChartApi | null = null;
    let handleResize: (() => void) | null = null;

    (async () => {
      const lc = await import("lightweight-charts");
      if (!chartContainerRef.current) return;

      chart = lc.createChart(chartContainerRef.current, {
        width: chartContainerRef.current.clientWidth,
        height: 400,
        layout: {
          background: { type: lc.ColorType.Solid, color: '#0a0a0f' },
          textColor: '#9ca3af',
        },
        grid: {
          vertLines: { color: '#1f2937' },
          horzLines: { color: '#1f2937' },
        },
        crosshair: { mode: lc.CrosshairMode.Normal },
        timeScale: { borderColor: '#374151' },
        rightPriceScale: { borderColor: '#374151' },
      });

      const candleSeries = chart.addSeries(lc.CandlestickSeries, {
        upColor: '#22c55e',
        downColor: '#ef4444',
        borderUpColor: '#22c55e',
        borderDownColor: '#ef4444',
        wickUpColor: '#22c55e',
        wickDownColor: '#ef4444',
      });
      // De-duplicate and sort by date (TradingView requires ascending unique times)
      const uniqueHistory = history.reduce((acc: typeof history, d) => {
        if (!acc.length || acc[acc.length - 1].date !== d.date) acc.push(d);
        return acc;
      }, []).sort((a, b) => a.date.localeCompare(b.date));

      candleSeries.setData(
        uniqueHistory.map((d) => ({
          time: d.date as string,
          open: d.open,
          high: d.high,
          low: d.low,
          close: d.close,
        }))
      );

      const sma20Series = chart.addSeries(lc.LineSeries, {
        color: '#5eead4',
        lineWidth: 1,
        title: 'SMA20',
      });
      const sma20Data = history
        .map((d, i) => ({
          time: d.date as string,
          value: indicators.sma20[i],
        }))
        .filter((d) => !isNaN(d.value));
      sma20Series.setData(sma20Data);

      const sma50Series = chart.addSeries(lc.LineSeries, {
        color: '#94a3b8',
        lineWidth: 1,
        title: 'SMA50',
      });
      const sma50Data = history
        .map((d, i) => ({
          time: d.date as string,
          value: indicators.sma50[i],
        }))
        .filter((d) => !isNaN(d.value));
      sma50Series.setData(sma50Data);

      const volumeSeries = chart.addSeries(lc.HistogramSeries, {
        priceFormat: { type: 'volume' },
        priceScaleId: 'volume',
      });
      chart.priceScale('volume').applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
      });
      volumeSeries.setData(
        uniqueHistory.map((d) => ({
          time: d.date as string,
          value: d.volume,
          color: d.close >= d.open ? '#22c55e40' : '#ef444440',
        }))
      );

      chart.timeScale().fitContent();

      handleResize = () => {
        chart?.applyOptions({ width: chartContainerRef.current!.clientWidth });
      };
      window.addEventListener('resize', handleResize);
    })();

    return () => {
      if (handleResize) window.removeEventListener('resize', handleResize);
      chart?.remove();
    };
  }, [history, indicators]);

  /* -- MACD Chart -- */
  useEffect(() => {
    if (!macdChartContainerRef.current || !history.length || !indicators) return;

    let chart: IChartApi | null = null;
    let handleResize: (() => void) | null = null;

    (async () => {
      const lc = await import("lightweight-charts");
      if (!macdChartContainerRef.current) return;

      chart = lc.createChart(macdChartContainerRef.current, {
        width: macdChartContainerRef.current.clientWidth,
        height: 200,
        layout: {
          background: { type: lc.ColorType.Solid, color: '#0a0a0f' },
          textColor: '#9ca3af',
        },
        grid: {
          vertLines: { color: '#1f2937' },
          horzLines: { color: '#1f2937' },
        },
        crosshair: { mode: lc.CrosshairMode.Normal },
        timeScale: { borderColor: '#374151' },
        rightPriceScale: { borderColor: '#374151' },
      });

      const histSeries = chart.addSeries(lc.HistogramSeries, {
        priceFormat: { type: 'price', precision: 4, minMove: 0.0001 },
      });
      histSeries.setData(
        history
          .map((d, i) => ({
            time: d.date as string,
            value: indicators.macd.histogram[i],
            color: indicators.macd.histogram[i] >= 0 ? '#22c55e' : '#ef4444',
          }))
          .filter((d) => !isNaN(d.value))
      );

      const macdLine = chart.addSeries(lc.LineSeries, {
        color: '#5eead4',
        lineWidth: 1,
        title: 'MACD',
      });
      macdLine.setData(
        history
          .map((d, i) => ({
            time: d.date as string,
            value: indicators.macd.macd[i],
          }))
          .filter((d) => !isNaN(d.value))
      );

      const signalLine = chart.addSeries(lc.LineSeries, {
        color: '#94a3b8',
        lineWidth: 1,
        title: 'Signal',
      });
      signalLine.setData(
        history
          .map((d, i) => ({
            time: d.date as string,
            value: indicators.macd.signal[i],
          }))
          .filter((d) => !isNaN(d.value))
      );

      chart.timeScale().fitContent();

      handleResize = () => {
        chart?.applyOptions({ width: macdChartContainerRef.current!.clientWidth });
      };
      window.addEventListener('resize', handleResize);
    })();

    return () => {
      if (handleResize) window.removeEventListener('resize', handleResize);
      chart?.remove();
    };
  }, [history, indicators]);

  /* -- Current values -- */
  const currentBar = last(history);
  const prevBar = history.length > 1 ? history[history.length - 2] : null;
  const price = currentBar?.close ?? 0;
  const prevClose = prevBar?.close ?? currentBar?.open ?? price;
  const change = prevClose > 0 ? ((price - prevClose) / prevClose) * 100 : 0;
  const isUp = change >= 0;

  const currentRSI = indicators ? lastNum(indicators.rsi) : NaN;
  const currentMACD = indicators ? lastNum(indicators.macd.macd) : NaN;
  const currentSignal = indicators ? lastNum(indicators.macd.signal) : NaN;
  const currentHist = indicators ? lastNum(indicators.macd.histogram) : NaN;
  const currentSMA20 = indicators ? lastNum(indicators.sma20) : NaN;
  const currentSMA50 = indicators ? lastNum(indicators.sma50) : NaN;
  const currentBBUpper = indicators ? lastNum(indicators.bb.upper) : NaN;
  const currentBBLower = indicators ? lastNum(indicators.bb.lower) : NaN;
  const currentK = indicators ? lastNum(indicators.kdj.k) : NaN;
  const currentD = indicators ? lastNum(indicators.kdj.d) : NaN;
  const currentJ = indicators ? lastNum(indicators.kdj.j) : NaN;

  /* -- Determine stock name -- */
  const tickerInfo = findTicker(code);
  const stockName = tickerInfo?.nameCn || tickerInfo?.name || code;

  /* -- Add to watchlist handler -- */
  const addToWatchlist = () => {
    try {
      const wl = JSON.parse(localStorage.getItem("finclaw_watchlist") || "[]") as string[];
      if (wl.includes(code)) {
        setWatchlistState("exists");
        return;
      }
      wl.push(code);
      localStorage.setItem("finclaw_watchlist", JSON.stringify(wl));
      setWatchlistState("added");
      setTimeout(() => setWatchlistState("exists"), 2000);
    } catch { /* ignore */ }
  };

  /* -- Analysis data -- */
  const analysis = useMemo(() => {
    if (!indicators || isNaN(currentRSI)) return null;
    return generateAnalysis(
      code,
      stockName,
      price,
      currentRSI,
      currentHist,
      currentSMA20,
      currentSMA50,
      cn,
    );
  }, [code, stockName, price, currentRSI, currentHist, currentSMA20, currentSMA50, cn, indicators]);

  /* -- Render -- */
  return (
    <div className="min-h-screen bg-[#0a0a0f] text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800/40 bg-[#0a0a0f]/90 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-4">
          <Link
            href="/"
            className="text-gray-400 hover:text-white transition-colors text-sm"
          >
            Back to Dashboard
          </Link>
          <div className="w-px h-5 bg-gray-700" />
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-white">{stockName}</h1>
            {tickerInfo?.nameCn && (
              <span className="text-sm text-gray-500 font-mono">{code}</span>
            )}
            <span className="px-2 py-0.5 text-xs rounded bg-gray-800/60 text-gray-400">
              {cn ? "A-Share" : crypto ? "Crypto" : "US"}
            </span>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={() => setShowAlertModal(true)}
              className="px-3 py-1.5 text-xs rounded border border-gray-700/50 text-gray-400 hover:text-white hover:border-gray-600 transition-colors"
            >
              Set Alert
            </button>
            <Link
              href={`/compare?a=${encodeURIComponent(code)}&b=`}
              className="px-3 py-1.5 text-xs rounded border border-gray-700/50 text-gray-400 hover:text-white hover:border-gray-600 transition-colors"
            >
              Compare
            </Link>
            <button
              onClick={addToWatchlist}
              disabled={watchlistState === "exists"}
              className={`px-3 py-1.5 text-xs rounded border transition-colors ${
                watchlistState === "exists"
                  ? "border-gray-700/30 text-gray-600 cursor-default"
                  : watchlistState === "added"
                    ? "border-green-800/50 text-[#22c55e]"
                    : "border-gray-700/50 text-gray-400 hover:text-white hover:border-gray-600"
              }`}
            >
              {watchlistState === "exists"
                ? "In Watchlist"
                : watchlistState === "added"
                  ? "Added"
                  : "Add to Watchlist"}
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin w-8 h-8 border-2 border-slate-500 border-t-transparent rounded-full" />
            <span className="ml-3 text-gray-400">Loading...</span>
          </div>
        )}

        {error && !loading && (
          <div className="text-center py-20">
            <p className="text-red-400 text-lg">{error}</p>
            <Link href="/" className="text-gray-400 text-sm mt-4 inline-block hover:text-white">
              Back to Dashboard
            </Link>
          </div>
        )}

        {!loading && !error && currentBar && (
          <>
            {/* -- Hero: Price & Stats Grid -- */}
            <section className="rounded border border-gray-800/60 bg-[#13131a] p-6">
              <div className="flex flex-wrap items-end gap-6 mb-4">
                <div>
                  <p className="text-4xl font-mono font-bold text-white">
                    {fmtP(price, cn)}
                  </p>
                  <span
                    className={`text-lg font-bold font-mono ${isUp ? "text-[#22c55e]" : "text-[#ef4444]"}`}
                  >
                    {isUp ? "+" : ""}{Math.abs(change).toFixed(2)}%
                  </span>
                </div>
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-x-6 gap-y-3 text-sm border-t border-gray-800/40 pt-4">
                <div>
                  <span className="text-gray-500 text-xs">Open</span>
                  <p className="font-mono text-gray-300">{fmtP(currentBar.open, cn)}</p>
                </div>
                <div>
                  <span className="text-gray-500 text-xs">High</span>
                  <p className="font-mono text-gray-300">{fmtP(currentBar.high, cn)}</p>
                </div>
                <div>
                  <span className="text-gray-500 text-xs">Low</span>
                  <p className="font-mono text-gray-300">{fmtP(currentBar.low, cn)}</p>
                </div>
                <div>
                  <span className="text-gray-500 text-xs">Volume</span>
                  <p className="font-mono text-gray-300">
                    {currentBar.volume > 0
                      ? cn
                        ? fmt.compactCn(currentBar.volume)
                        : fmt.compact(currentBar.volume)
                      : "\u2014"}
                  </p>
                </div>
                {week52 && (
                  <>
                    <div>
                      <span className="text-gray-500 text-xs">52w High</span>
                      <p className="font-mono text-gray-300">{fmtP(week52.high, cn)}</p>
                    </div>
                    <div>
                      <span className="text-gray-500 text-xs">52w Low</span>
                      <p className="font-mono text-gray-300">{fmtP(week52.low, cn)}</p>
                    </div>
                  </>
                )}
              </div>
            </section>

            {/* -- TradingView Price Chart + Time Range -- */}
            <section className="rounded border border-gray-800/60 bg-[#13131a] p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold text-gray-400">
                  Price ({history.length}d)
                </h2>
                <TimeRangeSelector selected={timeRange} onChange={setTimeRange} />
              </div>
              <div ref={chartContainerRef} />
            </section>

            {/* -- Technical Indicators Grid -- */}
            <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* RSI */}
              <div className="rounded border border-gray-800/60 bg-[#13131a] p-5">
                <h3 className="text-xs font-semibold text-gray-500 mb-3">RSI (14)</h3>
                <p
                  className={`text-3xl font-mono font-bold ${
                    currentRSI > 70
                      ? "text-[#ef4444]"
                      : currentRSI < 30
                        ? "text-[#22c55e]"
                        : "text-gray-200"
                  }`}
                >
                  {isNaN(currentRSI) ? "\u2014" : currentRSI.toFixed(1)}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {currentRSI > 70
                    ? "Overbought zone"
                    : currentRSI < 30
                      ? "Oversold zone"
                      : currentRSI > 60
                        ? "Above neutral"
                        : currentRSI < 40
                          ? "Below neutral"
                          : "Neutral range"}
                </p>
              </div>

              {/* MACD */}
              <div className="rounded border border-gray-800/60 bg-[#13131a] p-5">
                <h3 className="text-xs font-semibold text-gray-500 mb-3">MACD</h3>
                <div className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">MACD</span>
                    <span className="font-mono text-gray-300">
                      {isNaN(currentMACD) ? "\u2014" : currentMACD.toFixed(3)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Signal</span>
                    <span className="font-mono text-gray-300">
                      {isNaN(currentSignal) ? "\u2014" : currentSignal.toFixed(3)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Histogram</span>
                    <span
                      className={`font-mono font-bold ${
                        currentHist > 0 ? "text-[#22c55e]" : "text-[#ef4444]"
                      }`}
                    >
                      {isNaN(currentHist) ? "\u2014" : currentHist.toFixed(3)}
                    </span>
                  </div>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  {currentHist > 0 ? "Bullish crossover" : "Bearish crossover"}
                </p>
              </div>

              {/* Bollinger Bands */}
              <div className="rounded border border-gray-800/60 bg-[#13131a] p-5">
                <h3 className="text-xs font-semibold text-gray-500 mb-3">Bollinger Bands (20,2)</h3>
                <div className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Upper</span>
                    <span className="font-mono text-gray-300">
                      {isNaN(currentBBUpper) ? "\u2014" : fmtP(currentBBUpper, cn)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Middle</span>
                    <span className="font-mono text-gray-300">
                      {isNaN(currentSMA20) ? "\u2014" : fmtP(currentSMA20, cn)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Lower</span>
                    <span className="font-mono text-gray-300">
                      {isNaN(currentBBLower) ? "\u2014" : fmtP(currentBBLower, cn)}
                    </span>
                  </div>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  {price > currentBBUpper
                    ? "Price above upper band"
                    : price < currentBBLower
                      ? "Price below lower band"
                      : "Price within band range"}
                </p>
              </div>

              {/* KDJ */}
              <div className="rounded border border-gray-800/60 bg-[#13131a] p-5">
                <h3 className="text-xs font-semibold text-gray-500 mb-3">KDJ (9,3,3)</h3>
                <div className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">K</span>
                    <span className="font-mono text-gray-300">
                      {isNaN(currentK) ? "\u2014" : currentK.toFixed(1)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">D</span>
                    <span className="font-mono text-gray-300">
                      {isNaN(currentD) ? "\u2014" : currentD.toFixed(1)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">J</span>
                    <span
                      className={`font-mono ${
                        currentJ > 100 ? "text-[#ef4444]" : currentJ < 0 ? "text-[#22c55e]" : "text-gray-300"
                      }`}
                    >
                      {isNaN(currentJ) ? "\u2014" : currentJ.toFixed(1)}
                    </span>
                  </div>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  {currentK > currentD ? "K above D (bullish)" : "K below D (bearish)"}
                  {currentJ > 100 ? " / J overbought" : currentJ < 0 ? " / J oversold" : ""}
                </p>
              </div>

              {/* SMA */}
              <div className="rounded border border-gray-800/60 bg-[#13131a] p-5">
                <h3 className="text-xs font-semibold text-gray-500 mb-3">Moving Averages</h3>
                <div className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">SMA(20)</span>
                    <span className="font-mono text-gray-300">
                      {isNaN(currentSMA20) ? "\u2014" : fmtP(currentSMA20, cn)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">SMA(50)</span>
                    <span className="font-mono text-gray-300">
                      {isNaN(currentSMA50) ? "\u2014" : fmtP(currentSMA50, cn)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Trend</span>
                    <span className="font-mono text-gray-300">
                      {price > currentSMA20 && price > currentSMA50
                        ? "Bullish"
                        : price < currentSMA20 && price < currentSMA50
                          ? "Bearish"
                          : "Ranging"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Volume */}
              <div className="rounded border border-gray-800/60 bg-[#13131a] p-5">
                <h3 className="text-xs font-semibold text-gray-500 mb-3">Volume Summary</h3>
                <div className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Latest Volume</span>
                    <span className="font-mono text-gray-300">
                      {currentBar.volume > 0
                        ? cn
                          ? fmt.compactCn(currentBar.volume)
                          : fmt.compact(currentBar.volume)
                        : "\u2014"}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Data Period</span>
                    <span className="font-mono text-gray-300">{history.length}d</span>
                  </div>
                </div>
              </div>
            </section>

            {/* -- MACD Chart -- */}
            <section className="rounded border border-gray-800/60 bg-[#13131a] p-6">
              <h2 className="text-sm font-semibold text-gray-400 mb-4">MACD</h2>
              <div ref={macdChartContainerRef} />
            </section>

            {/* -- Fundamentals Panel (US stocks only) -- */}
            {!crypto && <FundamentalsPanel code={code} />}

            {/* -- Technical Analysis Summary -- */}
            {analysis && (
              <section className="rounded border border-gray-700/40 bg-[#13131a] p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-sm font-semibold text-gray-400">
                    Technical Analysis
                  </h2>
                  <span
                    className={`px-2 py-1 rounded text-xs font-mono font-bold ${
                      analysis.score >= 7
                        ? "bg-green-950/60 text-[#22c55e] border border-green-800/40"
                        : analysis.score <= 3
                          ? "bg-red-950/60 text-[#ef4444] border border-red-800/40"
                          : "bg-gray-800/60 text-gray-300 border border-gray-700/40"
                    }`}
                  >
                    {analysis.score}/10 {analysis.signalText}
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500 text-xs">RSI</span>
                    <p className="font-mono text-gray-300">{analysis.rsiInterp}</p>
                  </div>
                  <div>
                    <span className="text-gray-500 text-xs">MACD</span>
                    <p className="font-mono text-gray-300">{analysis.macdSignal}</p>
                  </div>
                  <div>
                    <span className="text-gray-500 text-xs">Stop-loss (-8%)</span>
                    <p className="font-mono text-gray-300">{analysis.stopLoss}</p>
                  </div>
                </div>
                <div className="mt-3 pt-3 border-t border-gray-800/40">
                  <p className="text-[10px] text-gray-600">
                    {analysis.factors.join(" / ")}
                  </p>
                </div>
                <p className="text-[10px] text-gray-600 mt-2">
                  Auto-generated from technical indicators. Not investment advice.
                </p>
              </section>
            )}
          </>
        )}
      </main>

      {/* Price Alert Modal */}
      {showAlertModal && (
        <SetAlertModal
          ticker={code}
          currentPrice={price}
          onClose={() => setShowAlertModal(false)}
        />
      )}

      {/* Footer */}
      <footer className="border-t border-gray-800/30 py-6 mt-12">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <p className="text-xs text-gray-600">
            FinClaw &middot; Open-source quantitative research platform
          </p>
        </div>
      </footer>
    </div>
  );
}
