"use client";

import { useState, useEffect, useCallback } from "react";

/* ════════════════════════════════════════════════════════════════
   DATA FRESHNESS INDICATOR
   Shows last data update time with color-coded status
   Green = fresh (<2 min), Yellow = stale (2-5 min), Red = offline (>5 min)
   ════════════════════════════════════════════════════════════════ */

type FreshnessStatus = "fresh" | "stale" | "offline";

function getStatus(ageMs: number): FreshnessStatus {
  if (ageMs < 120_000) return "fresh";    // < 2 min
  if (ageMs < 300_000) return "stale";    // < 5 min
  return "offline";                        // > 5 min
}

const STATUS_CONFIG: Record<
  FreshnessStatus,
  { dotColor: string; textColor: string; label: string }
> = {
  fresh:   { dotColor: "bg-[#22c55e]", textColor: "text-gray-500", label: "Live" },
  stale:   { dotColor: "bg-yellow-500", textColor: "text-yellow-600", label: "Stale" },
  offline: { dotColor: "bg-red-500",    textColor: "text-red-600",    label: "Offline" },
};

export default function DataFreshnessIndicator() {
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [status, setStatus] = useState<FreshnessStatus>("offline");
  const [timeStr, setTimeStr] = useState("");

  // Ping the API to check freshness
  const checkFreshness = useCallback(async () => {
    try {
      const resp = await fetch("/api/prices?market=us", { method: "HEAD" });
      if (resp.ok) {
        const now = new Date();
        setLastUpdate(now);
        setStatus("fresh");
      }
    } catch {
      if (lastUpdate) {
        const age = Date.now() - lastUpdate.getTime();
        setStatus(getStatus(age));
      } else {
        setStatus("offline");
      }
    }
  }, [lastUpdate]);

  // Initial check
  useEffect(() => {
    checkFreshness();
    const interval = setInterval(checkFreshness, 60_000); // Check every minute
    return () => clearInterval(interval);
  }, [checkFreshness]);

  // Update display time and status every second
  useEffect(() => {
    const tick = () => {
      if (lastUpdate) {
        const age = Date.now() - lastUpdate.getTime();
        setStatus(getStatus(age));
        setTimeStr(
          lastUpdate.toLocaleTimeString("en-US", { hour12: false })
        );
      }
    };
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [lastUpdate]);

  const config = STATUS_CONFIG[status];

  return (
    <div className="flex items-center gap-1.5" title={`Data ${config.label.toLowerCase()}`}>
      {/* Animated dot */}
      <span className="relative flex h-2 w-2">
        {status === "fresh" && (
          <span
            className={`animate-ping absolute inline-flex h-full w-full rounded-full ${config.dotColor} opacity-40`}
          />
        )}
        <span
          className={`relative inline-flex rounded-full h-2 w-2 ${config.dotColor}`}
        />
      </span>

      {/* Time */}
      <span className={`font-mono text-[10px] ${config.textColor}`}>
        {lastUpdate ? timeStr : "---"}
      </span>
    </div>
  );
}
