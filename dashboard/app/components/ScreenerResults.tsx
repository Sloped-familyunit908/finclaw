"use client";

import { useRouter } from "next/navigation";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/app/components/ui/table";
import { Badge } from "@/app/components/ui/badge";
import { Button } from "@/app/components/ui/button";

/* ── Types ── */
export interface ScreenerRow {
  asset: string;
  name?: string;
  nameCn?: string;
  price: number;
  change24h: number;
  volume24h: number | null;
  marketCap: number | null;
  market?: string;
}

type SortField =
  | "ticker"
  | "name"
  | "price"
  | "change"
  | "volume"
  | "marketCap"
  | "market";

/* ── Number formatting helpers ── */
function formatPrice(value: number, market?: string): string {
  const symbol = market === "A股" ? "\u00A5" : "$";
  if (value >= 10000) {
    return symbol + value.toLocaleString(undefined, { maximumFractionDigits: 0 });
  }
  if (value >= 1) {
    return symbol + value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return symbol + value.toLocaleString(undefined, { maximumFractionDigits: 4 });
}

function formatChange(value: number): string {
  const sign = value >= 0 ? "+" : "";
  return sign + value.toFixed(2) + "%";
}

function formatCompact(value: number | null, market?: string): string {
  if (value === null || value === undefined) return "--";
  const symbol = market === "A股" ? "\u00A5" : "$";
  const abs = Math.abs(value);
  if (abs >= 1e12) return symbol + (value / 1e12).toFixed(2) + "T";
  if (abs >= 1e9) return symbol + (value / 1e9).toFixed(1) + "B";
  if (abs >= 1e6) return symbol + (value / 1e6).toFixed(1) + "M";
  if (abs >= 1e3) return symbol + (value / 1e3).toFixed(1) + "K";
  return symbol + value.toLocaleString();
}

function formatVolume(value: number | null, market?: string): string {
  return formatCompact(value, market);
}

/* ── Sort icon ── */
function SortIndicator({
  field,
  currentSort,
  currentOrder,
}: {
  field: SortField;
  currentSort: SortField;
  currentOrder: "asc" | "desc";
}) {
  if (field !== currentSort) {
    return <span className="text-gray-700 ml-1">|</span>;
  }
  return (
    <span className="text-gray-400 ml-1">
      {currentOrder === "asc" ? "▲" : "▼"}
    </span>
  );
}

/* ── Loading skeleton ── */
function SkeletonRows() {
  return (
    <>
      {Array.from({ length: 8 }).map((_, i) => (
        <TableRow key={i}>
          {Array.from({ length: 7 }).map((_, j) => (
            <TableCell key={j}>
              <div className="h-3.5 bg-gray-800/60 rounded animate-pulse" />
            </TableCell>
          ))}
        </TableRow>
      ))}
    </>
  );
}

/* ── CSV export ── */
function exportCSV(data: ScreenerRow[]) {
  const headers = [
    "Ticker",
    "Name",
    "Last Price",
    "Change %",
    "Volume",
    "Market Cap",
    "Market",
  ];
  const rows = data.map((row) => [
    row.asset,
    row.nameCn || row.name || row.asset,
    row.price.toString(),
    row.change24h.toFixed(2) + "%",
    row.volume24h?.toString() ?? "",
    row.marketCap?.toString() ?? "",
    row.market ?? "",
  ]);

  const csv = [headers, ...rows].map((r) => r.map((c) => `"${c}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const date = new Date().toISOString().slice(0, 10);
  const a = document.createElement("a");
  a.href = url;
  a.download = `finclaw-screener-${date}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

/* ── Market badge ── */
function MarketBadge({ market }: { market?: string }) {
  let variant: "info" | "warning" | "purple" | "secondary" = "secondary";
  if (market === "US") variant = "info";
  else if (market === "A股") variant = "warning";
  else if (market === "Crypto") variant = "purple";

  return (
    <Badge variant={variant} className="text-[10px]">
      {market ?? "--"}
    </Badge>
  );
}

/* ── Main results component ── */
export default function ScreenerResults({
  data,
  total,
  loading,
  error,
  sortField,
  sortOrder,
  onSort,
  onRetry,
}: {
  data: ScreenerRow[];
  total: number;
  loading: boolean;
  error: string | null;
  sortField: SortField;
  sortOrder: "asc" | "desc";
  onSort: (field: SortField) => void;
  onRetry: () => void;
}) {
  const router = useRouter();

  const headerCols: { field: SortField; label: string; align: string }[] = [
    { field: "ticker", label: "Ticker", align: "text-left" },
    { field: "name", label: "Name", align: "text-left" },
    { field: "price", label: "Last Price", align: "text-right" },
    { field: "change", label: "Change %", align: "text-right" },
    { field: "volume", label: "Volume", align: "text-right" },
    { field: "marketCap", label: "Market Cap", align: "text-right" },
    { field: "market", label: "Market", align: "text-center" },
  ];

  /* Error state */
  if (error) {
    return (
      <div className="rounded-lg border border-red-900/40 bg-red-950/20 p-8 text-center">
        <p className="text-sm text-red-400">{error}</p>
        <Button
          variant="destructive"
          size="sm"
          onClick={onRetry}
          className="mt-4"
        >
          Retry
        </Button>
      </div>
    );
  }

  /* Empty state (only after loading) */
  if (!loading && data.length === 0) {
    return (
      <div className="rounded-lg border border-gray-800/50 bg-[#13131a] p-8 text-center">
        <p className="text-sm text-gray-400">
          No stocks match your filters. Try adjusting the criteria.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Results header */}
      <div className="flex items-center justify-between">
        <p className="text-xs text-gray-500 font-mono">
          {loading ? (
            <span className="animate-pulse">Loading...</span>
          ) : (
            <span>{total} stocks found</span>
          )}
        </p>
        {!loading && data.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => exportCSV(data)}
          >
            Export CSV
          </Button>
        )}
      </div>

      {/* Table */}
      <div className="rounded-lg border border-gray-800/50 bg-[#13131a] overflow-hidden">
        <Table className="text-xs">
          <TableHeader>
            <TableRow className="bg-gray-900/40 hover:bg-gray-900/40">
              {headerCols.map((col) => (
                <TableHead
                  key={col.field}
                  className={`cursor-pointer hover:text-gray-300 transition-colors select-none ${col.align}`}
                  onClick={() => onSort(col.field)}
                >
                  {col.label}
                  <SortIndicator
                    field={col.field}
                    currentSort={sortField}
                    currentOrder={sortOrder}
                  />
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <SkeletonRows />
            ) : (
              data.map((row) => (
                <TableRow
                  key={row.asset}
                  className="cursor-pointer"
                  onClick={() =>
                    router.push(`/stock/${encodeURIComponent(row.asset)}`)
                  }
                >
                  <TableCell className="font-mono font-semibold text-gray-200">
                    {row.asset}
                  </TableCell>
                  <TableCell className="text-gray-400 truncate max-w-[180px]">
                    {row.nameCn
                      ? `${row.nameCn}`
                      : row.name ?? row.asset}
                  </TableCell>
                  <TableCell className="text-right font-mono text-gray-200">
                    {formatPrice(row.price, row.market)}
                  </TableCell>
                  <TableCell
                    className={`text-right font-mono ${
                      row.change24h > 0
                        ? "text-emerald-400"
                        : row.change24h < 0
                          ? "text-red-400"
                          : "text-gray-400"
                    }`}
                  >
                    {formatChange(row.change24h)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-gray-400">
                    {formatVolume(row.volume24h, row.market)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-gray-400">
                    {formatCompact(row.marketCap, row.market)}
                  </TableCell>
                  <TableCell className="text-center">
                    <MarketBadge market={row.market} />
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
