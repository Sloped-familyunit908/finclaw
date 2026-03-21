"use client";

import { useState, useEffect, useCallback, useRef } from "react";

/* ── Filter state interface ── */
export interface ScreenerFilterValues {
  market: string;
  priceMin: string;
  priceMax: string;
  changeMin: string;
  changeMax: string;
  volumeMin: string;
  volumeMax: string;
}

export const DEFAULT_FILTERS: ScreenerFilterValues = {
  market: "all",
  priceMin: "",
  priceMax: "",
  changeMin: "",
  changeMax: "",
  volumeMin: "",
  volumeMax: "",
};

/* ── Active filter chip ── */
function FilterChip({
  label,
  onRemove,
}: {
  label: string;
  onRemove: () => void;
}) {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] bg-slate-800/60 border border-slate-700/50 rounded text-gray-300">
      {label}
      <button
        onClick={onRemove}
        className="ml-0.5 text-gray-500 hover:text-gray-300 transition-colors"
        aria-label={`Remove filter: ${label}`}
      >
        x
      </button>
    </span>
  );
}

/* ── Number input for range filters ── */
function RangeInput({
  label,
  minValue,
  maxValue,
  onMinChange,
  onMaxChange,
  minPlaceholder,
  maxPlaceholder,
}: {
  label: string;
  minValue: string;
  maxValue: string;
  onMinChange: (v: string) => void;
  onMaxChange: (v: string) => void;
  minPlaceholder?: string;
  maxPlaceholder?: string;
}) {
  return (
    <div className="space-y-1">
      <label className="text-[10px] text-gray-500 uppercase tracking-wider font-semibold">
        {label}
      </label>
      <div className="flex gap-1">
        <input
          type="number"
          value={minValue}
          onChange={(e) => onMinChange(e.target.value)}
          placeholder={minPlaceholder ?? "Min"}
          className="w-20 px-2 py-1.5 text-xs bg-gray-900/60 border border-gray-700/50 rounded text-gray-300 placeholder-gray-600 focus:outline-none focus:border-slate-500/60 font-mono [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
        />
        <input
          type="number"
          value={maxValue}
          onChange={(e) => onMaxChange(e.target.value)}
          placeholder={maxPlaceholder ?? "Max"}
          className="w-20 px-2 py-1.5 text-xs bg-gray-900/60 border border-gray-700/50 rounded text-gray-300 placeholder-gray-600 focus:outline-none focus:border-slate-500/60 font-mono [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
        />
      </div>
    </div>
  );
}

/* ── Main filter component ── */
export default function ScreenerFilters({
  filters,
  onChange,
}: {
  filters: ScreenerFilterValues;
  onChange: (filters: ScreenerFilterValues) => void;
}) {
  const [localFilters, setLocalFilters] =
    useState<ScreenerFilterValues>(filters);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync external changes
  useEffect(() => {
    setLocalFilters(filters);
  }, [filters]);

  // Debounced update
  const debouncedUpdate = useCallback(
    (newFilters: ScreenerFilterValues) => {
      setLocalFilters(newFilters);
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        onChange(newFilters);
      }, 500);
    },
    [onChange],
  );

  // Immediate update (for market select and reset)
  const immediateUpdate = useCallback(
    (newFilters: ScreenerFilterValues) => {
      setLocalFilters(newFilters);
      if (debounceRef.current) clearTimeout(debounceRef.current);
      onChange(newFilters);
    },
    [onChange],
  );

  const update = (key: keyof ScreenerFilterValues, value: string) => {
    const next = { ...localFilters, [key]: value };
    if (key === "market") {
      immediateUpdate(next);
    } else {
      debouncedUpdate(next);
    }
  };

  const resetAll = () => {
    immediateUpdate({ ...DEFAULT_FILTERS });
  };

  // Compute active filter chips
  const chips: { label: string; key: keyof ScreenerFilterValues }[] = [];
  const marketLabels: Record<string, string> = {
    us: "US",
    cn: "China A-Shares",
    crypto: "Crypto",
  };
  if (localFilters.market !== "all") {
    chips.push({
      label: `Market: ${marketLabels[localFilters.market] ?? localFilters.market}`,
      key: "market",
    });
  }
  if (localFilters.priceMin)
    chips.push({ label: `Price >= ${localFilters.priceMin}`, key: "priceMin" });
  if (localFilters.priceMax)
    chips.push({ label: `Price <= ${localFilters.priceMax}`, key: "priceMax" });
  if (localFilters.changeMin)
    chips.push({
      label: `Change >= ${localFilters.changeMin}%`,
      key: "changeMin",
    });
  if (localFilters.changeMax)
    chips.push({
      label: `Change <= ${localFilters.changeMax}%`,
      key: "changeMax",
    });
  if (localFilters.volumeMin)
    chips.push({
      label: `Volume >= ${Number(localFilters.volumeMin).toLocaleString()}`,
      key: "volumeMin",
    });
  if (localFilters.volumeMax)
    chips.push({
      label: `Volume <= ${Number(localFilters.volumeMax).toLocaleString()}`,
      key: "volumeMax",
    });

  const removeChip = (key: keyof ScreenerFilterValues) => {
    const defaults: Record<string, string> = {
      market: "all",
      priceMin: "",
      priceMax: "",
      changeMin: "",
      changeMax: "",
      volumeMin: "",
      volumeMax: "",
    };
    immediateUpdate({ ...localFilters, [key]: defaults[key] });
  };

  return (
    <div className="space-y-3">
      {/* Filter bar */}
      <div className="flex flex-wrap items-end gap-4">
        {/* Market dropdown */}
        <div className="space-y-1">
          <label className="text-[10px] text-gray-500 uppercase tracking-wider font-semibold">
            Market
          </label>
          <select
            value={localFilters.market}
            onChange={(e) => update("market", e.target.value)}
            className="px-2 py-1.5 text-xs bg-gray-900/60 border border-gray-700/50 rounded text-gray-300 focus:outline-none focus:border-slate-500/60 cursor-pointer"
          >
            <option value="all">All Markets</option>
            <option value="us">US</option>
            <option value="cn">China A-Shares</option>
            <option value="crypto">Crypto</option>
          </select>
        </div>

        {/* Price range */}
        <RangeInput
          label="Price"
          minValue={localFilters.priceMin}
          maxValue={localFilters.priceMax}
          onMinChange={(v) => update("priceMin", v)}
          onMaxChange={(v) => update("priceMax", v)}
        />

        {/* Change% range */}
        <RangeInput
          label="Change %"
          minValue={localFilters.changeMin}
          maxValue={localFilters.changeMax}
          onMinChange={(v) => update("changeMin", v)}
          onMaxChange={(v) => update("changeMax", v)}
          minPlaceholder="Min %"
          maxPlaceholder="Max %"
        />

        {/* Volume range */}
        <RangeInput
          label="Volume"
          minValue={localFilters.volumeMin}
          maxValue={localFilters.volumeMax}
          onMinChange={(v) => update("volumeMin", v)}
          onMaxChange={(v) => update("volumeMax", v)}
          minPlaceholder="Min"
          maxPlaceholder="Max"
        />

        {/* Reset button */}
        <div className="space-y-1">
          <label className="text-[10px] text-transparent select-none">_</label>
          <button
            onClick={resetAll}
            className="px-3 py-1.5 text-xs text-gray-400 hover:text-gray-200 bg-gray-800/40 hover:bg-gray-800/60 border border-gray-700/40 rounded transition-colors"
          >
            Reset
          </button>
        </div>
      </div>

      {/* Active filter chips */}
      {chips.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {chips.map((chip) => (
            <FilterChip
              key={chip.key}
              label={chip.label}
              onRemove={() => removeChip(chip.key)}
            />
          ))}
          <span className="text-[10px] text-gray-600 self-center ml-1">
            {chips.length} active
          </span>
        </div>
      )}
    </div>
  );
}
