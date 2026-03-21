/* ════════════════════════════════════════════════════════════════
   ECONOMIC EVENTS — FinClaw
   Generates upcoming economic events from known schedules
   ════════════════════════════════════════════════════════════════ */

export interface EconomicEvent {
  date: string;       // ISO date string YYYY-MM-DD
  time: string;       // Display time e.g. "08:30 ET"
  name: string;
  importance: "high" | "medium" | "low";
}

/* ── FOMC Meeting dates for 2025-2026 (published by the Fed) ── */
const FOMC_DATES_2025 = [
  "2025-01-29", "2025-03-19", "2025-05-07",
  "2025-06-18", "2025-07-30", "2025-09-17",
  "2025-11-05", "2025-12-17",
];
const FOMC_DATES_2026 = [
  "2026-01-28", "2026-03-18", "2026-05-06",
  "2026-06-17", "2026-07-29", "2026-09-16",
  "2026-11-04", "2026-12-16",
];

/* ── Helper: get Nth weekday of month ── */
function nthWeekday(year: number, month: number, weekday: number, n: number): Date {
  const first = new Date(year, month, 1);
  let day = 1 + ((weekday - first.getDay() + 7) % 7);
  day += (n - 1) * 7;
  return new Date(year, month, day);
}

/* ── Generate NFP dates (first Friday of each month) ── */
function getNFPDates(year: number): string[] {
  const dates: string[] = [];
  for (let m = 0; m < 12; m++) {
    const d = nthWeekday(year, m, 5, 1); // 5 = Friday
    dates.push(d.toISOString().split("T")[0]);
  }
  return dates;
}

/* ── Generate CPI release dates (~12th-14th of each month) ── */
function getCPIDates(year: number): string[] {
  const dates: string[] = [];
  for (let m = 0; m < 12; m++) {
    // CPI is typically released on the second Tuesday or Wednesday
    const d = nthWeekday(year, m, 3, 2); // 2nd Wednesday
    dates.push(d.toISOString().split("T")[0]);
  }
  return dates;
}

/* ── GDP release dates (end of Jan, Apr, Jul, Oct) ── */
function getGDPDates(year: number): string[] {
  return [
    `${year}-01-30`, `${year}-04-30`, `${year}-07-30`, `${year}-10-30`,
  ];
}

/* ── Earnings season approximate start dates ── */
function getEarningsSeasonDates(year: number): string[] {
  return [
    `${year}-01-13`, // Q4 earnings
    `${year}-04-14`, // Q1 earnings
    `${year}-07-14`, // Q2 earnings
    `${year}-10-13`, // Q3 earnings
  ];
}

export function getUpcomingEvents(count: number = 5): EconomicEvent[] {
  const now = new Date();
  const today = now.toISOString().split("T")[0];
  const year = now.getFullYear();

  const allEvents: EconomicEvent[] = [];

  // FOMC meetings
  const fomcDates = [...FOMC_DATES_2025, ...FOMC_DATES_2026];
  for (const date of fomcDates) {
    allEvents.push({
      date,
      time: "14:00 ET",
      name: "FOMC Rate Decision",
      importance: "high",
    });
  }

  // NFP
  const nfpAll = [...getNFPDates(year), ...getNFPDates(year + 1)];
  for (const date of nfpAll) {
    allEvents.push({
      date,
      time: "08:30 ET",
      name: "Non-Farm Payrolls",
      importance: "high",
    });
  }

  // CPI
  const cpiAll = [...getCPIDates(year), ...getCPIDates(year + 1)];
  for (const date of cpiAll) {
    allEvents.push({
      date,
      time: "08:30 ET",
      name: "CPI Release",
      importance: "high",
    });
  }

  // GDP
  const gdpAll = [...getGDPDates(year), ...getGDPDates(year + 1)];
  for (const date of gdpAll) {
    allEvents.push({
      date,
      time: "08:30 ET",
      name: "GDP Report",
      importance: "medium",
    });
  }

  // Earnings season
  const earningsAll = [...getEarningsSeasonDates(year), ...getEarningsSeasonDates(year + 1)];
  for (const date of earningsAll) {
    allEvents.push({
      date,
      time: "—",
      name: "Earnings Season Begins",
      importance: "medium",
    });
  }

  // Filter to upcoming events only & sort by date
  const upcoming = allEvents
    .filter((e) => e.date >= today)
    .sort((a, b) => a.date.localeCompare(b.date));

  return upcoming.slice(0, count);
}
