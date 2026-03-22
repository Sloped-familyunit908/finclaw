"use client";

import { useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/app/components/ui/card";
import { Badge } from "@/app/components/ui/badge";

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
    import("@/app/lib/economicEvents").then(({ getUpcomingEvents }) => {
      setEvents(getUpcomingEvents(5));
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Economic Calendar</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[140px] flex items-center justify-center">
            <div className="animate-spin w-5 h-5 border-2 border-slate-600 border-t-transparent rounded-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle>Economic Calendar</CardTitle>
      </CardHeader>
      <CardContent>
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

                  {/* Importance badge */}
                  <Badge
                    variant={
                      event.importance === "high"
                        ? "destructive"
                        : event.importance === "medium"
                          ? "warning"
                          : "secondary"
                    }
                    className="text-[9px] px-1 py-0"
                  >
                    {event.importance === "high"
                      ? "HIGH"
                      : event.importance === "medium"
                        ? "MED"
                        : "LOW"}
                  </Badge>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
