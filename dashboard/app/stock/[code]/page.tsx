"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from "recharts";
import type { HistoryBar } from "@/app/api/history/route";
import {
  calcRSI,
  calcMACD,
  calcBollingerBands,
  calcSMA,
  calcKDJ,
} from "@/app/lib/indicators";
import { fmt } from "@/app/lib/utils";

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
  const macdSignal = macdHist > 0 ? "bullish crossover" : "bearish crossover";
  const maAbove20 = price > sma20;
  const maAbove50 = price > sma50;
  const maAnalysis = maAbove20 && maAbove50
    ? "Price above both MA20 and MA50; bullish alignment"
    : !maAbove20 && !maAbove50
      ? "Price below both MA20 and MA50; bearish alignment"
      : maAbove20
        ? "Price above MA20 but below MA50; mixed"
        : "Price below MA20, near MA50 support";

  let score = 5;
  const factors: string[] = [];

  if (rsi > 40 && rsi < 60) { score += 1; factors.push("RSI neutral range (+1)"); }
  else if (rsi < 30) { score += 2; factors.push("RSI oversold opportunity (+2)"); }
  else if (rsi > 70) { score -= 1; factors.push("RSI overbought risk (-1)"); }

  if (macdHist > 0) { score += 1; factors.push("MACD bullish crossover (+1)"); }
  else { score -= 1; factors.push("MACD bearish crossover (-1)"); }

  if (maAbove20 && maAbove50) { score += 2; factors.push("Bullish MA alignment (+2)"); }
  else if (!maAbove20 && !maAbove50) { score -= 1; factors.push("Bearish MA alignment (-1)"); }

  score = Math.max(1, Math.min(10, score));

  const signalText = score >= 7 ? "Bullish" : score <= 3 ? "Bearish" : "Neutral";
  const stopLoss = price * 0.92;
  const currency = cn ? "¥" : "$";

  return `Technical Analysis Summary — ${name} (${code})

Technicals: RSI(14) at ${rsi.toFixed(1)}, ${rsiInterp} zone. MACD ${macdSignal}. ${maAnalysis}.

Composite Score: ${score}/10 (${signalText})
Score Factors: ${factors.join("; ")}

Risk Note: This analysis is derived from technical indicators only and does not constitute investment advice. Suggested stop-loss: ${currency}${stopLoss.toFixed(2)} (-8%).`;
}

/* -- Candlestick via SVG in Recharts -- */
interface CandleProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  payload?: any;
}
function CandlestickShape({ x = 0, y = 0, width = 0, payload }: CandleProps) {
  if (!payload) return null;
  const { open, close, high, low, yScale } = payload;
  if (!yScale) return null;

  const isUp = close >= open;
  const color = isUp ? "#22c55e" : "#ef4444";
  const bodyTop = yScale(Math.max(open, close));
  const bodyBot = yScale(Math.min(open, close));
  const bodyH = Math.max(bodyBot - bodyTop, 1);
  const wickX = x + width / 2;

  return (
    <g>
      <line x1={wickX} y1={yScale(high)} x2={wickX} y2={yScale(low)} stroke={color} strokeWidth={1} />
      <rect x={x + 1} y={bodyTop} width={Math.max(width - 2, 2)} height={bodyH} fill={color} rx={1} />
    </g>
  );
}

/* ================================================================ */
export default function StockDetailPage() {
  const params = useParams();
  const code = decodeURIComponent(params.code as string);
  const cn = isCN(code);
  const crypto = isCrypto(code);

  const [history, setHistory] = useState<HistoryBar[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);

    fetch(`/api/history?code=${encodeURIComponent(code)}&days=60`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setHistory(data);
        } else {
          setError("No data available");
        }
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [code]);

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

  /* -- Build chart data -- */
  const chartData = useMemo(() => {
    if (!indicators) return [];

    return history.map((bar, i) => ({
      date: bar.date.slice(5), // MM-DD
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close,
      volume: bar.volume,
      range: [Math.min(bar.open, bar.close), Math.max(bar.open, bar.close)],
      sma20: indicators.sma20[i],
      sma50: indicators.sma50[i],
      bbUpper: indicators.bb.upper[i],
      bbLower: indicators.bb.lower[i],
      rsi: indicators.rsi[i],
      macdLine: indicators.macd.macd[i],
      macdSignal: indicators.macd.signal[i],
      macdHist: indicators.macd.histogram[i],
    }));
  }, [history, indicators]);

  /* -- Determine stock name -- */
  const stockName = code;

  /* -- Analysis text -- */
  const analysisText = useMemo(() => {
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
            Back to Overview
          </Link>
          <div className="w-px h-5 bg-gray-700" />
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-white">{stockName}</h1>
            <span className="px-2 py-0.5 text-xs rounded bg-gray-800/60 text-gray-400">
              {cn ? "A-Share" : crypto ? "Crypto" : "US"}
            </span>
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
              Back to Overview
            </Link>
          </div>
        )}

        {!loading && !error && currentBar && (
          <>
            {/* -- Hero: Price & Change -- */}
            <section className="rounded border border-gray-800/60 bg-[#13131a] p-6">
              <div className="flex flex-wrap items-end gap-6">
                <div>
                  <p className="text-4xl font-mono font-bold text-white">
                    {fmtP(price, cn)}
                  </p>
                  <span
                    className={`text-lg font-bold font-mono ${isUp ? "text-green-400" : "text-red-400"}`}
                  >
                    {isUp ? "+" : ""}{Math.abs(change).toFixed(2)}%
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-8 gap-y-2 text-sm">
                  <div>
                    <span className="text-gray-500">Open</span>
                    <p className="font-mono text-gray-300">{fmtP(currentBar.open, cn)}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">High</span>
                    <p className="font-mono text-gray-300">{fmtP(currentBar.high, cn)}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Low</span>
                    <p className="font-mono text-gray-300">{fmtP(currentBar.low, cn)}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Volume</span>
                    <p className="font-mono text-gray-300">
                      {currentBar.volume > 0
                        ? cn
                          ? fmt.compactCn(currentBar.volume)
                          : fmt.compact(currentBar.volume)
                        : "—"}
                    </p>
                  </div>
                </div>
              </div>
            </section>

            {/* -- Price Chart -- */}
            <section className="rounded border border-gray-800/60 bg-[#13131a] p-6">
              <h2 className="text-sm font-semibold text-gray-400 mb-4">
                Price ({history.length}d)
              </h2>
              <div className="h-[360px]">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={chartData} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" />
                    <XAxis
                      dataKey="date"
                      tick={{ fill: "#6b7280", fontSize: 10 }}
                      tickLine={false}
                      axisLine={{ stroke: "#1e1e2e" }}
                    />
                    <YAxis
                      domain={["auto", "auto"]}
                      tick={{ fill: "#6b7280", fontSize: 10 }}
                      tickLine={false}
                      axisLine={false}
                      width={60}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#1a1a2e",
                        border: "1px solid #2a2a3a",
                        borderRadius: 4,
                        fontSize: 12,
                      }}
                      labelStyle={{ color: "#9ca3af" }}
                    />
                    {/* Bollinger Bands */}
                    <Line type="monotone" dataKey="bbUpper" stroke="#4b5563" strokeDasharray="4 2" dot={false} name="BB Upper" />
                    <Line type="monotone" dataKey="bbLower" stroke="#4b5563" strokeDasharray="4 2" dot={false} name="BB Lower" />
                    {/* Moving Averages */}
                    <Line type="monotone" dataKey="sma20" stroke="#5eead4" dot={false} strokeWidth={1.5} name="SMA20" />
                    <Line type="monotone" dataKey="sma50" stroke="#94a3b8" dot={false} strokeWidth={1.5} name="SMA50" />
                    {/* Close price line */}
                    <Line type="monotone" dataKey="close" stroke="#e4e4ef" dot={false} strokeWidth={2} name="Close" />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </section>

            {/* -- Technical Indicators Grid -- */}
            <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* RSI */}
              <div className="rounded border border-gray-800/60 bg-[#13131a] p-5">
                <h3 className="text-xs font-semibold text-gray-500 mb-3">RSI (14)</h3>
                <p
                  className={`text-3xl font-mono font-bold ${
                    currentRSI > 70
                      ? "text-red-400"
                      : currentRSI < 30
                        ? "text-green-400"
                        : "text-gray-200"
                  }`}
                >
                  {isNaN(currentRSI) ? "—" : currentRSI.toFixed(1)}
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
                      {isNaN(currentMACD) ? "—" : currentMACD.toFixed(3)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Signal</span>
                    <span className="font-mono text-gray-300">
                      {isNaN(currentSignal) ? "—" : currentSignal.toFixed(3)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Histogram</span>
                    <span
                      className={`font-mono font-bold ${
                        currentHist > 0 ? "text-green-400" : "text-red-400"
                      }`}
                    >
                      {isNaN(currentHist) ? "—" : currentHist.toFixed(3)}
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
                      {isNaN(currentBBUpper) ? "—" : fmtP(currentBBUpper, cn)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Middle</span>
                    <span className="font-mono text-gray-300">
                      {isNaN(currentSMA20) ? "—" : fmtP(currentSMA20, cn)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Lower</span>
                    <span className="font-mono text-gray-300">
                      {isNaN(currentBBLower) ? "—" : fmtP(currentBBLower, cn)}
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
                      {isNaN(currentK) ? "—" : currentK.toFixed(1)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">D</span>
                    <span className="font-mono text-gray-300">
                      {isNaN(currentD) ? "—" : currentD.toFixed(1)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">J</span>
                    <span
                      className={`font-mono ${
                        currentJ > 100 ? "text-red-400" : currentJ < 0 ? "text-green-400" : "text-gray-300"
                      }`}
                    >
                      {isNaN(currentJ) ? "—" : currentJ.toFixed(1)}
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
                      {isNaN(currentSMA20) ? "—" : fmtP(currentSMA20, cn)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">SMA(50)</span>
                    <span className="font-mono text-gray-300">
                      {isNaN(currentSMA50) ? "—" : fmtP(currentSMA50, cn)}
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
                        : "—"}
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
              <div className="h-[200px]">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={chartData} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" />
                    <XAxis
                      dataKey="date"
                      tick={{ fill: "#6b7280", fontSize: 10 }}
                      tickLine={false}
                      axisLine={{ stroke: "#1e1e2e" }}
                    />
                    <YAxis
                      tick={{ fill: "#6b7280", fontSize: 10 }}
                      tickLine={false}
                      axisLine={false}
                      width={50}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#1a1a2e",
                        border: "1px solid #2a2a3a",
                        borderRadius: 4,
                        fontSize: 12,
                      }}
                    />
                    <ReferenceLine y={0} stroke="#4b5563" />
                    <Bar
                      dataKey="macdHist"
                      name="Histogram"
                      fill="#5eead4"
                      // eslint-disable-next-line @typescript-eslint/no-explicit-any
                      shape={(props: any) => {
                        const { x, y, width, height, payload } = props;
                        const val = payload?.macdHist ?? 0;
                        return (
                          <rect
                            x={x}
                            y={val >= 0 ? y : y}
                            width={width}
                            height={Math.abs(height)}
                            fill={val >= 0 ? "#22c55e" : "#ef4444"}
                            rx={1}
                          />
                        );
                      }}
                    />
                    <Line type="monotone" dataKey="macdLine" stroke="#5eead4" dot={false} strokeWidth={1.5} name="MACD" />
                    <Line type="monotone" dataKey="macdSignal" stroke="#94a3b8" dot={false} strokeWidth={1.5} name="Signal" />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </section>

            {/* -- Technical Analysis -- */}
            {analysisText && (
              <section className="rounded border border-gray-700/40 bg-[#13131a] p-6">
                <h2 className="text-sm font-semibold text-gray-400 mb-4">
                  Technical Analysis Summary
                </h2>
                <pre className="whitespace-pre-wrap text-sm text-gray-300 font-mono leading-relaxed">
                  {analysisText}
                </pre>
                <p className="text-[10px] text-gray-600 mt-4 border-t border-gray-800/50 pt-3">
                  This analysis is auto-generated from technical indicators and is provided for informational purposes only. Not investment advice.
                </p>
              </section>
            )}
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800/30 py-6 mt-12">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <p className="text-xs text-gray-600">
            FinClaw &copy; {new Date().getFullYear()}
          </p>
        </div>
      </footer>
    </div>
  );
}
