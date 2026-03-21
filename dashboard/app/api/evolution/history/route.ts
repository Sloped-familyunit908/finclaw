/* ════════════════════════════════════════════════════════════════
   API ROUTE — /api/evolution/history
   Reads ALL gen_XXXX.json files and returns timeline data
   ════════════════════════════════════════════════════════════════ */

import { NextResponse } from "next/server";
import { readdir, readFile } from "fs/promises";
import { existsSync } from "fs";
import path from "path";

/* ── Simple in-memory cache (60 s) ── */
let cachedData: { data: unknown; ts: number } | null = null;
const CACHE_TTL = 60_000;

interface GenResult {
  annual_return: number;
  max_drawdown: number;
  win_rate: number;
  sharpe: number;
  calmar: number;
  total_trades: number;
  profit_factor: number;
  fitness: number;
  dna: Record<string, number>;
}

interface GenFile {
  generation: number;
  timestamp: string;
  results: GenResult[];
}

interface TimelinePoint {
  generation: number;
  timestamp: string;
  bestFitness: number;
  annualReturn: number;
  sharpe: number;
  maxDrawdown: number;
  winRate: number;
  calmar: number;
  totalTrades: number;
  profitFactor: number;
}

interface HistoryResponse {
  timeline: TimelinePoint[];
  topStrategies: (GenResult & { generation: number })[];
  totalGenerations: number;
}

export async function GET() {
  // Check cache
  if (cachedData && Date.now() - cachedData.ts < CACHE_TTL) {
    return NextResponse.json(cachedData.data);
  }

  try {
    // Find evolution_results directory
    const candidates = [
      path.resolve(process.cwd(), "..", "evolution_results"),
      path.resolve(process.cwd(), "..", "..", "evolution_results"),
      path.resolve(process.cwd(), "evolution_results"),
    ];

    let dirPath = "";
    for (const p of candidates) {
      if (existsSync(p)) {
        dirPath = p;
        break;
      }
    }

    if (!dirPath) {
      const empty: HistoryResponse = { timeline: [], topStrategies: [], totalGenerations: 0 };
      cachedData = { data: empty, ts: Date.now() };
      return NextResponse.json(empty);
    }

    // Read all gen_XXXX.json files
    const files = await readdir(dirPath);
    const genFiles = files
      .filter((f) => /^gen_\d+\.json$/.test(f))
      .sort((a, b) => {
        const numA = parseInt(a.match(/\d+/)![0], 10);
        const numB = parseInt(b.match(/\d+/)![0], 10);
        return numA - numB;
      });

    const timeline: TimelinePoint[] = [];
    let latestResults: GenResult[] = [];
    let latestGen = 0;

    // Read all gen files in parallel with concurrency limit
    const BATCH = 50;
    for (let i = 0; i < genFiles.length; i += BATCH) {
      const batch = genFiles.slice(i, i + BATCH);
      const results = await Promise.all(
        batch.map(async (file) => {
          try {
            const raw = await readFile(path.join(dirPath, file), "utf-8");
            return JSON.parse(raw) as GenFile;
          } catch {
            return null;
          }
        })
      );

      for (const gen of results) {
        if (!gen || !gen.results || gen.results.length === 0) continue;

        const best = gen.results[0]; // Already sorted by fitness in the file
        timeline.push({
          generation: gen.generation,
          timestamp: gen.timestamp,
          bestFitness: best.fitness,
          annualReturn: best.annual_return,
          sharpe: best.sharpe,
          maxDrawdown: best.max_drawdown,
          winRate: best.win_rate,
          calmar: best.calmar,
          totalTrades: best.total_trades,
          profitFactor: best.profit_factor,
        });

        if (gen.generation > latestGen) {
          latestGen = gen.generation;
          latestResults = gen.results;
        }
      }
    }

    // Sort timeline by generation
    timeline.sort((a, b) => a.generation - b.generation);

    // Get top 5 strategies from latest generation
    const topStrategies = latestResults
      .slice(0, 5)
      .map((r) => ({ ...r, generation: latestGen }));

    const response: HistoryResponse = {
      timeline,
      topStrategies,
      totalGenerations: latestGen,
    };

    cachedData = { data: response, ts: Date.now() };
    return NextResponse.json(response);
  } catch {
    const empty: HistoryResponse = { timeline: [], topStrategies: [], totalGenerations: 0 };
    cachedData = { data: empty, ts: Date.now() };
    return NextResponse.json(empty);
  }
}
