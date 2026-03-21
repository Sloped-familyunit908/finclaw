/* ════════════════════════════════════════════════════════════════
   API ROUTE — /api/evolution  — FinClaw
   Returns the latest evolution engine results (if available)
   ════════════════════════════════════════════════════════════════ */

import { NextResponse } from "next/server";
import { readFile } from "fs/promises";
import { existsSync } from "fs";
import path from "path";

/* ── Simple in-memory cache (30 s) ── */
let cachedData: { data: unknown; ts: number } | null = null;
const CACHE_TTL = 30_000;

export async function GET() {
  // Check cache
  if (cachedData && Date.now() - cachedData.ts < CACHE_TTL) {
    return NextResponse.json(cachedData.data);
  }

  try {
    // Try multiple possible paths — cwd is usually dashboard/
    const candidates = [
      path.resolve(process.cwd(), "..", "evolution_results", "latest.json"),
      path.resolve(process.cwd(), "..", "..", "evolution_results", "latest.json"),
      path.resolve(process.cwd(), "evolution_results", "latest.json"),
    ];

    let filePath = "";
    for (const p of candidates) {
      if (existsSync(p)) {
        filePath = p;
        break;
      }
    }

    if (!filePath) {
      const empty = null;
      cachedData = { data: empty, ts: Date.now() };
      return NextResponse.json(empty);
    }

    const raw = await readFile(filePath, "utf-8");
    const json = JSON.parse(raw);

    // Normalize the data shape — handle both flat and nested formats
    const best = json.results?.[0] ?? json;
    const result = {
      generation: json.generation ?? best.generation ?? 0,
      timestamp: json.timestamp ?? new Date().toISOString(),
      bestFitness: best.fitness ?? json.bestFitness ?? json.best_fitness ?? 0,
      annualReturn: best.annual_return ?? json.annualReturn ?? json.annual_return ?? 0,
      sharpe: best.sharpe ?? json.sharpe ?? 0,
      winRate: best.win_rate ?? json.winRate ?? json.win_rate ?? 0,
      maxDrawdown: best.max_drawdown ?? json.maxDrawdown ?? json.max_drawdown ?? 0,
      totalTrades: best.total_trades ?? json.totalTrades ?? json.total_trades ?? 0,
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
