/* ════════════════════════════════════════════════════════════════
   API ROUTE — /api/evolution  — FinClaw
   Returns the latest evolution engine results (if available)
   ════════════════════════════════════════════════════════════════ */

import { NextResponse } from "next/server";
import { readFile } from "fs/promises";
import { join } from "path";

/* ── Simple in-memory cache (30 s) ── */
let cachedData: { data: unknown; ts: number } | null = null;
const CACHE_TTL = 30_000;

export async function GET() {
  // Check cache
  if (cachedData && Date.now() - cachedData.ts < CACHE_TTL) {
    return NextResponse.json(cachedData.data);
  }

  try {
    const filePath = join(process.cwd(), "..", "..", "evolution_results", "latest.json");
    const raw = await readFile(filePath, "utf-8");
    const json = JSON.parse(raw);

    // Normalize the data shape
    const result = {
      generation: json.generation ?? 0,
      timestamp: json.timestamp ?? new Date().toISOString(),
      bestFitness: json.bestFitness ?? json.best_fitness ?? 0,
      annualReturn: json.annualReturn ?? json.annual_return ?? 0,
      sharpe: json.sharpe ?? 0,
      winRate: json.winRate ?? json.win_rate ?? 0,
      dimensions: json.dimensions ?? 41,
      stockCount: json.stockCount ?? json.stock_count ?? 500,
    };

    cachedData = { data: result, ts: Date.now() };
    return NextResponse.json(result);
  } catch {
    // File doesn't exist or can't be read — return null gracefully
    const empty = null;
    cachedData = { data: empty, ts: Date.now() };
    return NextResponse.json(empty);
  }
}
