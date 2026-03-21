"use client";

/* ════════════════════════════════════════════════════════════════
   TIME RANGE SELECTOR — Stock Detail Page
   Buttons: 1W | 1M | 3M | 6M | 1Y | All
   ════════════════════════════════════════════════════════════════ */

export type TimeRange = "1w" | "1m" | "3m" | "6m" | "1y" | "all";

const RANGES: { value: TimeRange; label: string }[] = [
  { value: "1w", label: "1W" },
  { value: "1m", label: "1M" },
  { value: "3m", label: "3M" },
  { value: "6m", label: "6M" },
  { value: "1y", label: "1Y" },
  { value: "all", label: "All" },
];

export default function TimeRangeSelector({
  selected,
  onChange,
}: {
  selected: TimeRange;
  onChange: (range: TimeRange) => void;
}) {
  return (
    <div className="flex items-center gap-1">
      {RANGES.map((r) => (
        <button
          key={r.value}
          onClick={() => onChange(r.value)}
          className={`px-3 py-1 text-xs font-mono font-medium rounded transition-all ${
            selected === r.value
              ? "bg-slate-700/50 text-white border border-slate-500/50"
              : "text-gray-500 hover:text-gray-300 hover:bg-gray-800/40 border border-transparent"
          }`}
        >
          {r.label}
        </button>
      ))}
    </div>
  );
}
