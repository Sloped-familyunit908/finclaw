"use client";

/* ════════════════════════════════════════════════════════════════
   LOADING CARD — Reusable skeleton component
   ════════════════════════════════════════════════════════════════ */

interface LoadingCardProps {
  /** Number of skeleton rows to display */
  rows?: number;
  /** Optional title shown at top */
  title?: string;
  /** Show a chart-like skeleton area */
  chart?: boolean;
  /** Height of chart area in px */
  chartHeight?: number;
  /** Additional CSS classes */
  className?: string;
}

function SkeletonLine({ width = "w-full" }: { width?: string }) {
  return (
    <div
      className={`h-3 ${width} bg-gray-800/80 rounded animate-pulse`}
      style={{ animationDelay: `${Math.random() * 0.3}s` }}
    />
  );
}

export default function LoadingCard({
  rows = 4,
  title,
  chart = false,
  chartHeight = 200,
  className = "",
}: LoadingCardProps) {
  return (
    <div
      className={`rounded border border-gray-800/60 bg-[#13131a] p-5 ${className}`}
    >
      {title && (
        <div className="mb-4">
          <div className="h-3 w-32 bg-gray-800/80 rounded animate-pulse" />
        </div>
      )}

      {chart && (
        <div
          className="w-full bg-gray-900/40 rounded mb-4 animate-pulse"
          style={{ height: chartHeight }}
        />
      )}

      <div className="space-y-3">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex justify-between items-center gap-4">
            <SkeletonLine width={`w-${[24, 32, 20, 28, 36][i % 5]}`} />
            <SkeletonLine width="w-16" />
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Inline skeleton variants ── */

export function LoadingTable({
  columns = 5,
  rows = 6,
}: {
  columns?: number;
  rows?: number;
}) {
  return (
    <div className="overflow-x-auto rounded border border-gray-800/60">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-900/50">
            {Array.from({ length: columns }).map((_, i) => (
              <th key={i} className="py-2.5 px-3">
                <div className="h-3 w-16 bg-gray-800/80 rounded animate-pulse" />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, r) => (
            <tr key={r} className="border-t border-gray-800/30">
              {Array.from({ length: columns }).map((_, c) => (
                <td key={c} className="py-2.5 px-3">
                  <div
                    className="h-4 bg-gray-800/60 rounded animate-pulse"
                    style={{
                      width: `${50 + Math.random() * 40}%`,
                      animationDelay: `${r * 0.05}s`,
                    }}
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function LoadingMetric() {
  return (
    <div className="space-y-2 animate-pulse">
      <div className="h-3 w-20 bg-gray-800/80 rounded" />
      <div className="h-8 w-28 bg-gray-800/60 rounded" />
    </div>
  );
}
