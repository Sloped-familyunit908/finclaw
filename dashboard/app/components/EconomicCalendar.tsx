"use client";

import { useEffect, useState } from "react";

interface EconomicEvent {
  date: string;
  time: string;
  name: string;
  importance: "high" | "medium" | "low";
}

const IMPORTANCE_DOT: Record<string, string> = {
  high: "bg-red-500",
  medium: "bg-yellow-500",
  low: "bg-gray-500",
};

const IMPORTANCE_LABEL: Record<string, string> = {
  high: "text-red-400",
  medium: "text-yellow-400",
  low: "text-gray-500",
};

function formatEventDate(dateStr: string): string {
  const d = new Date(dateStr + "T12:00:00");
  const now = new Date();
  const today = now.toISOString().split("T")[0];
  const tomorrow = new Date(now.getTime() + 86400000)
    .toISOString()
    .split("T")[0];

  if (dateStr === today) return "Today";
  if (dateStr === tomorrow) return "Tomorrow";

  const month = d.toLocaleString("en-US", { month: "short" });
  const day = d.getDate();
  return `${month} ${day}`;
}

function daysUntil(dateStr: string): number {
  const now = new Date();
  const target = new Date(dateStr + "T12:00:00");
  return Math.ceil((target.getTime() - now.getTime()) / 86400000);
}

export default function EconomicCalendar() {
  const [events, setEvents] = useState<EconomicEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // We use the lib function via an inline import to generate events client-side
    // This avoids needing another API route for static schedule data
    import("@/app/lib/economicEvents").then(({ getUpcomingEvents }) => {
      setEvents(getUpcomingEvents(5));
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <section className="rounded border border-gray-800/60 bg-[#13131a] p-4">
        <h2 className="text-xs font-semibold text-gray-500 tracking-wider uppercase mb-3">
          Economic Calendar
        </h2>
        <div className="h-[140px] flex items-center justify-center">
          <div className="animate-spin w-5 h-5 border-2 border-slate-600 border-t-transparent rounded-full" />
        </div>
      </section>
    );
  }

  return (
    <section className="rounded border border-gray-800/60 bg-[#13131a] p-4">
      <h2 className="text-xs font-semibold text-gray-500 tracking-wider uppercase mb-3">
        Economic Calendar
      </h2>

      {events.length === 0 ? (
        <p className="text-xs text-gray-600 py-4 text-center">
          No upcoming events this week
        </p>
      ) : (
        <div className="space-y-[6px]">
          {events.map((event, i) => {
            const days = daysUntil(event.date);
            const isImminent = days <= 1;

            return (
              <div
                key={`${event.date}-${event.name}-${i}`}
                className={`flex items-center gap-3 py-[6px] px-2 rounded ${
                  isImminent
                    ? "bg-gray-800/40"
                    : "hover:bg-gray-800/20"
                } transition-colors`}
              >
                {/* Importance dot */}
                <div
                  className={`w-[6px] h-[6px] rounded-full shrink-0 ${IMPORTANCE_DOT[event.importance]}`}
                />

                {/* Date column */}
                <div className="w-[60px] shrink-0">
                  <span
                    className={`text-xs font-mono ${
                      isImminent ? "text-white font-bold" : "text-gray-400"
                    }`}
                  >
                    {formatEventDate(event.date)}
                  </span>
                </div>

                {/* Event name */}
                <div className="flex-1 min-w-0">
                  <span className="text-xs text-gray-300 truncate block">
                    {event.name}
                  </span>
                </div>

                {/* Time */}
                <span className="text-[10px] font-mono text-gray-600 shrink-0">
                  {event.time}
                </span>

                {/* Importance label */}
                <span
                  className={`text-[9px] font-mono uppercase shrink-0 ${IMPORTANCE_LABEL[event.importance]}`}
                >
                  {event.importance === "high"
                    ? "HIGH"
                    : event.importance === "medium"
                      ? "MED"
                      : "LOW"}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
