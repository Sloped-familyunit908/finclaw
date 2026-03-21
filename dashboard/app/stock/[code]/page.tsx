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

/* ── Helpers ── */
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

/* ── AI Analysis template ── */
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
    rsi > 70 ? "超买" : rsi < 30 ? "超卖" : rsi > 60 ? "偏强" : rsi < 40 ? "偏弱" : "中性";
  const macdSignal = macdHist > 0 ? "金叉看多" : "死叉看空";
  const maAbove20 = price > sma20;
  const maAbove50 = price > sma50;
  const maAnalysis = maAbove20 && maAbove50
    ? "站上MA20和MA50,多头排列"
    : !maAbove20 && !maAbove50
      ? "跌破MA20和MA50,空头排列"
      : maAbove20
        ? "站上MA20但未突破MA50"
        : "跌破MA20,处于MA50附近";

  let score = 5;
  const factors: string[] = [];

  if (rsi > 40 && rsi < 60) { score += 1; factors.push("RSI中性区间(+1)"); }
  else if (rsi < 30) { score += 2; factors.push("RSI超卖机会(+2)"); }
  else if (rsi > 70) { score -= 1; factors.push("RSI超买风险(-1)"); }

  if (macdHist > 0) { score += 1; factors.push("MACD金叉(+1)"); }
  else { score -= 1; factors.push("MACD死叉(-1)"); }

  if (maAbove20 && maAbove50) { score += 2; factors.push("均线多头(+2)"); }
  else if (!maAbove20 && !maAbove50) { score -= 1; factors.push("均线空头(-1)"); }

  score = Math.max(1, Math.min(10, score));

  const signalText = score >= 7 ? "偏多" : score <= 3 ? "偏空" : "中性";
  const stopLoss = price * 0.92;
  const currency = cn ? "¥" : "$";

  return `🦀 螃蟹分析 — ${name} (${code})

技术面: RSI ${rsi.toFixed(1)} (${rsiInterp}), MACD ${macdSignal}, ${maAnalysis}

进化策略评分: ${score}/10 (${signalText})
主要得分来源: ${factors.join(", ")}

风险提示: 以上分析仅基于技术指标,不构成投资建议. 止损位建议: ${currency}${stopLoss.toFixed(2)} (-8%)`;
}

/* ── Candlestick via SVG in Recharts ── */
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

/* ════════════════════════════════════════════════════════════════ */
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
          setError("暂无数据");
        }
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [code]);

  /* ── Compute indicators ── */
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

  /* ── Current values ── */
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

  /* ── Build chart data ── */
  const chartData = useMemo(() => {
    if (!indicators) return [];

    // Build yScale reference for candlesticks
    const allPrices = history.flatMap((b) => [b.high, b.low]);
    const minP = Math.min(...allPrices);
    const maxP = Math.max(...allPrices);

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

  /* ── Determine stock name ── */
  const stockName = code; // Will be enhanced when live data arrives

  /* ── Analysis text ── */
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

  /* ── Render ── */
  return (
    <div className="min-h-screen bg-[#0a0a0f] text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800/40 bg-[#0a0a0f]/90 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-4">
          <Link
            href="/"
            className="text-gray-400 hover:text-orange-400 transition-colors text-sm flex items-center gap-1"
          >
            ← 返回仪表盘
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-white">{stockName}</h1>
            <span className="px-2 py-0.5 text-xs rounded bg-gray-800/60 text-gray-400">
              {cn ? "A股" : crypto ? "Crypto" : "US"}
            </span>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin w-8 h-8 border-2 border-orange-500 border-t-transparent rounded-full" />
            <span className="ml-3 text-gray-400">加载中...</span>
          </div>
        )}

        {error && !loading && (
          <div className="text-center py-20">
            <p className="text-red-400 text-lg">{error}</p>
            <Link href="/" className="text-orange-400 text-sm mt-4 inline-block hover:underline">
              ← 返回
            </Link>
          </div>
        )}

        {!loading && !error && currentBar && (
          <>
            {/* ── Hero: Price & Change ── */}
            <section className="rounded-xl border border-gray-800/60 bg-[#13131a] p-6">
              <div className="flex flex-wrap items-end gap-6">
                <div>
                  <p className="text-4xl font-mono font-bold text-white">
                    {fmtP(price, cn)}
                  </p>
                  <span
                    className={`text-lg font-bold ${isUp ? "text-green-400" : "text-red-400"}`}
                  >
                    {isUp ? "▲" : "▼"} {Math.abs(change).toFixed(2)}%
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-8 gap-y-2 text-sm">
                  <div>
                    <span className="text-gray-500">开盘</span>
                    <p className="font-mono text-gray-300">{fmtP(currentBar.open, cn)}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">最高</span>
                    <p className="font-mono text-gray-300">{fmtP(currentBar.high, cn)}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">最低</span>
                    <p className="font-mono text-gray-300">{fmtP(currentBar.low, cn)}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">成交量</span>
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

            {/* ── Price Chart ── */}
            <section className="rounded-xl border border-gray-800/60 bg-[#13131a] p-6">
              <h2 className="text-sm font-semibold text-gray-400 mb-4">
                📈 价格走势 (近{history.length}日)
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
                        borderRadius: 8,
                        fontSize: 12,
                      }}
                      labelStyle={{ color: "#9ca3af" }}
                    />
                    {/* Bollinger Bands */}
                    <Line type="monotone" dataKey="bbUpper" stroke="#4b5563" strokeDasharray="4 2" dot={false} name="BB上轨" />
                    <Line type="monotone" dataKey="bbLower" stroke="#4b5563" strokeDasharray="4 2" dot={false} name="BB下轨" />
                    {/* Moving Averages */}
                    <Line type="monotone" dataKey="sma20" stroke="#f59e0b" dot={false} strokeWidth={1.5} name="SMA20" />
                    <Line type="monotone" dataKey="sma50" stroke="#8b5cf6" dot={false} strokeWidth={1.5} name="SMA50" />
                    {/* Close price line (as proxy for candlestick bodies) */}
                    <Line type="monotone" dataKey="close" stroke="#e4e4ef" dot={false} strokeWidth={2} name="收盘价" />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </section>

            {/* ── Technical Indicators Grid ── */}
            <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* RSI */}
              <div className="rounded-xl border border-gray-800/60 bg-[#13131a] p-5">
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
                    ? "⚠️ 超买区域"
                    : currentRSI < 30
                      ? "✅ 超卖区域"
                      : currentRSI > 60
                        ? "偏强"
                        : currentRSI < 40
                          ? "偏弱"
                          : "中性区间"}
                </p>
              </div>

              {/* MACD */}
              <div className="rounded-xl border border-gray-800/60 bg-[#13131a] p-5">
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
                  {currentHist > 0 ? "🟢 金叉" : "🔴 死叉"}
                </p>
              </div>

              {/* Bollinger Bands */}
              <div className="rounded-xl border border-gray-800/60 bg-[#13131a] p-5">
                <h3 className="text-xs font-semibold text-gray-500 mb-3">布林带 (20,2)</h3>
                <div className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">上轨</span>
                    <span className="font-mono text-gray-300">
                      {isNaN(currentBBUpper) ? "—" : fmtP(currentBBUpper, cn)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">中轨</span>
                    <span className="font-mono text-gray-300">
                      {isNaN(currentSMA20) ? "—" : fmtP(currentSMA20, cn)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">下轨</span>
                    <span className="font-mono text-gray-300">
                      {isNaN(currentBBLower) ? "—" : fmtP(currentBBLower, cn)}
                    </span>
                  </div>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  {price > currentBBUpper
                    ? "⚠️ 突破上轨"
                    : price < currentBBLower
                      ? "✅ 跌破下轨"
                      : "价格在通道内"}
                </p>
              </div>

              {/* KDJ */}
              <div className="rounded-xl border border-gray-800/60 bg-[#13131a] p-5">
                <h3 className="text-xs font-semibold text-gray-500 mb-3">KDJ (9,3,3)</h3>
                <div className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">K</span>
                    <span className="font-mono text-yellow-400">
                      {isNaN(currentK) ? "—" : currentK.toFixed(1)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">D</span>
                    <span className="font-mono text-blue-400">
                      {isNaN(currentD) ? "—" : currentD.toFixed(1)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">J</span>
                    <span
                      className={`font-mono ${
                        currentJ > 100 ? "text-red-400" : currentJ < 0 ? "text-green-400" : "text-purple-400"
                      }`}
                    >
                      {isNaN(currentJ) ? "—" : currentJ.toFixed(1)}
                    </span>
                  </div>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  {currentK > currentD ? "🟢 K上穿D" : "🔴 K下穿D"}
                  {currentJ > 100 ? " · J超买" : currentJ < 0 ? " · J超卖" : ""}
                </p>
              </div>

              {/* SMA */}
              <div className="rounded-xl border border-gray-800/60 bg-[#13131a] p-5">
                <h3 className="text-xs font-semibold text-gray-500 mb-3">均线系统</h3>
                <div className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">SMA(20)</span>
                    <span className="font-mono text-orange-400">
                      {isNaN(currentSMA20) ? "—" : fmtP(currentSMA20, cn)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">SMA(50)</span>
                    <span className="font-mono text-purple-400">
                      {isNaN(currentSMA50) ? "—" : fmtP(currentSMA50, cn)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">价格位置</span>
                    <span className="font-mono text-gray-300">
                      {price > currentSMA20 && price > currentSMA50
                        ? "多头"
                        : price < currentSMA20 && price < currentSMA50
                          ? "空头"
                          : "震荡"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Volume */}
              <div className="rounded-xl border border-gray-800/60 bg-[#13131a] p-5">
                <h3 className="text-xs font-semibold text-gray-500 mb-3">成交概况</h3>
                <div className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">今日成交量</span>
                    <span className="font-mono text-gray-300">
                      {currentBar.volume > 0
                        ? cn
                          ? fmt.compactCn(currentBar.volume)
                          : fmt.compact(currentBar.volume)
                        : "—"}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">数据天数</span>
                    <span className="font-mono text-gray-300">{history.length}天</span>
                  </div>
                </div>
              </div>
            </section>

            {/* ── MACD Chart ── */}
            <section className="rounded-xl border border-gray-800/60 bg-[#13131a] p-6">
              <h2 className="text-sm font-semibold text-gray-400 mb-4">📊 MACD</h2>
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
                        borderRadius: 8,
                        fontSize: 12,
                      }}
                    />
                    <ReferenceLine y={0} stroke="#4b5563" />
                    <Bar
                      dataKey="macdHist"
                      name="Histogram"
                      fill="#f59e0b"
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
                    <Line type="monotone" dataKey="macdLine" stroke="#f59e0b" dot={false} strokeWidth={1.5} name="MACD" />
                    <Line type="monotone" dataKey="macdSignal" stroke="#8b5cf6" dot={false} strokeWidth={1.5} name="Signal" />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </section>

            {/* ── AI Analysis ── */}
            {analysisText && (
              <section className="rounded-xl border border-orange-800/30 bg-[#13131a] p-6">
                <h2 className="text-sm font-semibold text-orange-400 mb-4">
                  🦀 螃蟹 AI 分析
                </h2>
                <pre className="whitespace-pre-wrap text-sm text-gray-300 font-mono leading-relaxed">
                  {analysisText}
                </pre>
                <p className="text-[10px] text-gray-600 mt-4 border-t border-gray-800/50 pt-3">
                  ⚠️ 本分析由技术指标模板自动生成，仅供参考，不构成任何投资建议。后续将接入 LLM 提供更深度分析。
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
            Built with 🦀 by{" "}
            <span className="text-orange-500/70">NeuZhou</span> — FinClaw
          </p>
        </div>
      </footer>
    </div>
  );
}
