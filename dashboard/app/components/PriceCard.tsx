import Link from "next/link";
import type { MarketData } from "@/app/types";
import { fmt } from "@/app/lib/utils";

export default function PriceCard({ data }: { data: MarketData }) {
  const isUp = data.change24h >= 0;
  const priceVsSma200 = data.sma200
    ? ((data.price - data.sma200) / data.sma200) * 100
    : null;
  const isCn = data.market === "A股";
  const fmtPrice = isCn ? fmt.cny(data.price) : fmt.usd(data.price);

  return (
    <Link href={`/stock/${encodeURIComponent(data.asset)}`} className="block">
      <div className="group rounded-xl border border-gray-800/60 bg-[#13131a] p-4 sm:p-5 hover:border-orange-800/40 transition-all hover:shadow-lg hover:shadow-orange-950/10 cursor-pointer">
        <div className="flex justify-between items-start mb-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-bold text-gray-100 truncate">
                {data.nameCn || data.asset}
              </h3>
              {data.market && (
                <span className="px-1.5 py-0.5 text-[9px] rounded bg-gray-800/60 text-gray-500 shrink-0">
                  {data.market}
                </span>
              )}
            </div>
            {data.nameCn && (
              <p className="text-xs text-gray-500 mt-0.5">{data.asset}</p>
            )}
            <p className="text-2xl font-mono font-bold mt-1 text-white">
              {fmtPrice}
            </p>
          </div>
          <span
            className={`px-3 py-1.5 rounded-lg text-sm font-bold shrink-0 ${
              isUp
                ? "bg-green-950/60 text-green-400 border border-green-800/40"
                : "bg-red-950/60 text-red-400 border border-red-800/40"
            }`}
          >
            {isUp ? "▲" : "▼"} {Math.abs(data.change24h).toFixed(2)}%
          </span>
        </div>

        <div className="grid grid-cols-2 gap-y-2 gap-x-4 text-xs">
          <div className="flex justify-between">
            <span className="text-gray-500">RSI(14)</span>
            <span
              className={`font-mono ${
                (data.rsi14 ?? 50) < 30
                  ? "text-green-400"
                  : (data.rsi14 ?? 50) > 70
                    ? "text-red-400"
                    : "text-gray-300"
              }`}
            >
              {data.rsi14?.toFixed(1) ?? "—"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Volume</span>
            <span className="font-mono text-gray-300">
              {data.volume24h
                ? isCn
                  ? fmt.compactCn(data.volume24h)
                  : fmt.compact(data.volume24h)
                : "—"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">SMA(20)</span>
            <span className="font-mono text-gray-300">
              {data.sma20
                ? isCn
                  ? fmt.cny(data.sma20)
                  : fmt.usd(data.sma20)
                : "—"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">SMA(50)</span>
            <span className="font-mono text-gray-300">
              {data.sma50
                ? isCn
                  ? fmt.cny(data.sma50)
                  : fmt.usd(data.sma50)
                : "—"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">SMA(200)</span>
            <span className="font-mono text-gray-300">
              {data.sma200
                ? isCn
                  ? fmt.cny(data.sma200)
                  : fmt.usd(data.sma200)
                : "—"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">vs SMA200</span>
            <span
              className={`font-mono ${
                priceVsSma200 !== null && priceVsSma200 < -20
                  ? "text-red-400"
                  : priceVsSma200 !== null && priceVsSma200 > 0
                    ? "text-green-400"
                    : "text-orange-400"
              }`}
            >
              {priceVsSma200 !== null ? fmt.pctRaw(priceVsSma200, 1) : "—"}
            </span>
          </div>
        </div>

        {data.marketCap && (
          <div className="mt-3 pt-3 border-t border-gray-800/50 text-xs text-gray-500">
            Market Cap:{" "}
            {isCn ? fmt.compactCn(data.marketCap) : fmt.compact(data.marketCap)}
          </div>
        )}
      </div>
    </Link>
  );
}
