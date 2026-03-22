"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardHeader, CardTitle, CardContent } from "@/app/components/ui/card";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/app/components/ui/table";

/* ── Types ── */
interface CryptoItem {
  rank: number;
  id: string;
  symbol: string;
  name: string;
  price: number;
  change24h: number;
  marketCap: number;
  volume24h: number;
}

/* ── Formatting ── */
function fmtUsd(n: number): string {
  if (n >= 100) return "$" + n.toLocaleString(undefined, { maximumFractionDigits: 0 });
  if (n >= 1) return "$" + n.toFixed(2);
  if (n >= 0.01) return "$" + n.toFixed(4);
  return "$" + n.toFixed(6);
}

function fmtCompact(n: number): string {
  if (n >= 1e12) return "$" + (n / 1e12).toFixed(2) + "T";
  if (n >= 1e9) return "$" + (n / 1e9).toFixed(1) + "B";
  if (n >= 1e6) return "$" + (n / 1e6).toFixed(1) + "M";
  return "$" + n.toLocaleString();
}

/* ── Component ── */
export default function CryptoMarketTable() {
  const router = useRouter();
  const [data, setData] = useState<CryptoItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const resp = await fetch("/api/crypto");
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const json = await resp.json();
        if (!cancelled && Array.isArray(json)) {
          // Show top 10 on homepage
          setData(json.slice(0, 10));
        }
      } catch {
        // silent
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    const interval = setInterval(load, 60_000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  if (loading) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Crypto Market</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[200px] flex items-center justify-center">
            <div className="animate-spin w-5 h-5 border-2 border-slate-600 border-t-transparent rounded-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Crypto Market</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-gray-600 text-center py-6">
            Unable to load crypto data
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle>Crypto Market</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="bg-gray-900/50 hover:bg-gray-900/50">
                <TableHead className="text-left pl-4 w-10">#</TableHead>
                <TableHead className="text-left">Coin</TableHead>
                <TableHead className="text-right">Price</TableHead>
                <TableHead className="text-right">24h%</TableHead>
                <TableHead className="text-right pr-4 hidden sm:table-cell">
                  Market Cap
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((coin) => {
                const isUp = coin.change24h >= 0;
                return (
                  <TableRow
                    key={coin.id}
                    className="cursor-pointer"
                    onClick={() =>
                      router.push(`/stock/${encodeURIComponent(coin.symbol)}`)
                    }
                  >
                    <TableCell className="pl-4 font-mono text-gray-600 text-xs">
                      {coin.rank}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-semibold text-gray-100 text-xs">
                          {coin.symbol}
                        </span>
                        <span className="text-gray-500 text-[11px] truncate max-w-[100px] hidden md:inline">
                          {coin.name}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="text-right font-mono text-gray-200 text-xs">
                      {fmtUsd(coin.price)}
                    </TableCell>
                    <TableCell
                      className={`text-right font-mono font-bold text-xs ${
                        isUp ? "text-[#22c55e]" : "text-[#ef4444]"
                      }`}
                    >
                      {isUp ? "+" : ""}
                      {coin.change24h.toFixed(2)}%
                    </TableCell>
                    <TableCell className="text-right pr-4 font-mono text-gray-400 text-xs hidden sm:table-cell">
                      {fmtCompact(coin.marketCap)}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
