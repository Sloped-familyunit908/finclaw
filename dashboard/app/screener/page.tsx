"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import ScreenerFilters, {
  type ScreenerFilterValues,
  DEFAULT_FILTERS,
} from "@/app/components/ScreenerFilters";
import ScreenerResults, {
  type ScreenerRow,
} from "@/app/components/ScreenerResults";

type SortField =
  | "ticker"
  | "name"
  | "price"
  | "change"
  | "volume"
  | "marketCap"
  | "market";

/* ── Build query string from filters ── */
function buildQuery(
  filters: ScreenerFilterValues,
  sortField: SortField,
  sortOrder: "asc" | "desc",
): string {
  const params = new URLSearchParams();
  params.set("market", filters.market);
  if (filters.priceMin) params.set("priceMin", filters.priceMin);
  if (filters.priceMax) params.set("priceMax", filters.priceMax);
  if (filters.changeMin) params.set("changeMin", filters.changeMin);
  if (filters.changeMax) params.set("changeMax", filters.changeMax);
  if (filters.volumeMin) params.set("volumeMin", filters.volumeMin);
  if (filters.volumeMax) params.set("volumeMax", filters.volumeMax);
  params.set("sort", sortField);
  params.set("order", sortOrder);
  return params.toString();
}

export default function ScreenerPage() {
  const [filters, setFilters] = useState<ScreenerFilterValues>(DEFAULT_FILTERS);
  const [sortField, setSortField] = useState<SortField>("change");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [data, setData] = useState<ScreenerRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nlQuery, setNlQuery] = useState("");

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const qs = buildQuery(filters, sortField, sortOrder);
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 15000);

      const resp = await fetch(`/api/screener?${qs}`, {
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (!resp.ok) {
        throw new Error(`Server error (${resp.status})`);
      }

      const json = await resp.json();
      if (json.error) {
        throw new Error(json.error);
      }

      setData(json.data ?? []);
      setTotal(json.total ?? 0);
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === "AbortError") {
        setError("Request timed out. Please try again.");
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("An unexpected error occurred.");
      }
      setData([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [filters, sortField, sortOrder]);

  // Fetch on filters/sort change
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSort = (field: SortField) => {
    if (field === sortField) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  };

  const handleFiltersChange = (newFilters: ScreenerFilterValues) => {
    setFilters(newFilters);
  };

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-gray-100">
      {/* Header with back nav */}
      <header className="border-b border-gray-800/50 bg-[#0a0a0f]/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="text-xl font-bold text-white tracking-tight hover:opacity-80 transition-opacity"
            >
              FinClaw
            </Link>
            <span className="text-gray-700">|</span>
            <h1 className="text-sm font-semibold text-gray-300">
              Stock Screener
            </h1>
          </div>
          <Link
            href="/"
            className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
          >
            Back to Dashboard
          </Link>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* Natural language input */}
        <div className="rounded border border-gray-800/50 bg-[#13131a] p-4">
          <div className="flex gap-2">
            <div className="flex-1">
              <input
                type="text"
                value={nlQuery}
                onChange={(e) => setNlQuery(e.target.value)}
                placeholder="Describe what you're looking for... (requires LLM in finclaw.config.ts)"
                disabled
                className="w-full px-3 py-2 text-xs bg-gray-900/60 border border-gray-700/50 rounded text-gray-500 placeholder-gray-600 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>
            <button
              disabled
              className="px-4 py-2 text-xs bg-slate-700/40 border border-slate-600/50 rounded text-gray-500 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Go
            </button>
          </div>
          <p className="text-[10px] text-gray-600 mt-1.5">
            Natural language search requires LLM configuration. Configure in
            finclaw.config.ts to enable.
          </p>
        </div>

        {/* Filters */}
        <div className="rounded border border-gray-800/50 bg-[#13131a] p-4">
          <ScreenerFilters filters={filters} onChange={handleFiltersChange} />
        </div>

        {/* Results */}
        <ScreenerResults
          data={data}
          total={total}
          loading={loading}
          error={error}
          sortField={sortField}
          sortOrder={sortOrder}
          onSort={handleSort}
          onRetry={fetchData}
        />
      </main>

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
