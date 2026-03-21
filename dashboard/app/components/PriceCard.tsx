import Link from "next/link";
import type { MarketData } from "@/app/types";
import { fmt } from "@/app/lib/utils";

export default function PriceCard({ data }: { data: MarketData }) {
  const isUp = data.change24h >= 0;
  const isCn = data.market === "A股";
  const fmtPrice = isCn ? fmt.cny(data.price) : fmt.usd(data.price);

  return (
    <Link href={`/stock/${encodeURIComponent(data.asset)}`} className="block">
      <div className="group rounded border border-gray-800/60 bg-[#13131a] px-3 py-2.5 hover:border-slate-600/50 transition-all cursor-pointer">
        {/* Row 1: Name + Change badge */}
        <div className="flex justify-between items-start mb-1.5">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-gray-100 truncate">
                {data.nameCn || data.asset}
              </h3>
              {data.market && (
                <span className="px-1.5 py-0.5 text-[9px] rounded bg-gray-800/60 text-gray-500 shrink-0">
                  {data.market}
                </span>
              )}
            </div>
            {data.nameCn && (
              <p className="text-xs text-gray-500 mt-0.5 font-mono">{data.asset}</p>
            )}
          </div>
          <span
            className={`px-2 py-0.5 rounded text-sm font-bold font-mono shrink-0 ${
              isUp
                ? "bg-green-950/60 text-green-400 border border-green-800/40"
                : "bg-red-950/60 text-red-400 border border-red-800/40"
            }`}
          >
            {isUp ? "+" : ""}{data.change24h.toFixed(2)}%
          </span>
        </div>

        {/* Row 2: Price — prominent */}
        <p className="text-xl font-mono font-bold text-white mb-2">
          {fmtPrice}
        </p>

        {/* Row 3: Volume + Market Cap in one line */}
        <div className="flex justify-between items-center text-xs text-gray-500">
          <span>
            Vol{" "}
            <span className="font-mono text-gray-400">
              {data.volume24h
                ? isCn
                  ? fmt.compactCn(data.volume24h)
                  : fmt.compact(data.volume24h)
                : "—"}
            </span>
          </span>
          {data.marketCap && (
            <span>
              Mkt{" "}
              <span className="font-mono text-gray-400">
                {isCn ? fmt.compactCn(data.marketCap) : fmt.compact(data.marketCap)}
              </span>
            </span>
          )}
        </div>

        {/* Hover indicator */}
        <div className="mt-1.5 text-[10px] text-gray-600 opacity-0 group-hover:opacity-100 transition-opacity text-right">
          View details ›
        </div>
      </div>
    </Link>
  );
}
