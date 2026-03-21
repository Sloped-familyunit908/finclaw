"use client";

import { useState, useEffect } from "react";

/* ── Types ── */
interface NewsItem {
  title: string;
  url: string;
  source: string;
  publishedAt: string;
  sentiment?: "positive" | "negative" | "neutral";
}

/* ── Relative time helper ── */
function timeAgo(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  if (isNaN(then)) return "";

  const diffMs = now - then;
  const diffMin = Math.floor(diffMs / 60_000);
  const diffHr = Math.floor(diffMs / 3_600_000);
  const diffDay = Math.floor(diffMs / 86_400_000);

  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHr < 24) return `${diffHr}h ago`;
  if (diffDay < 30) return `${diffDay}d ago`;
  return `${Math.floor(diffDay / 30)}mo ago`;
}

/* ── Extract display domain ── */
function displayDomain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}

/* ── Sentiment badge ── */
function SentimentBadge({ sentiment }: { sentiment: "positive" | "negative" | "neutral" }) {
  const config = {
    positive: { label: "Positive", className: "text-green-400" },
    negative: { label: "Negative", className: "text-red-400" },
    neutral: { label: "Neutral", className: "text-gray-500" },
  };

  const { label, className } = config[sentiment];

  return (
    <span className={`text-[10px] font-semibold uppercase tracking-wider ${className}`}>
      [{label}]
    </span>
  );
}

/* ── Loading skeleton ── */
function NewsSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="animate-pulse flex flex-col gap-1.5">
          <div className="h-4 bg-gray-800 rounded w-full" />
          <div className="h-3 bg-gray-800/60 rounded w-40" />
        </div>
      ))}
    </div>
  );
}

/* ── NewsPanel component ── */
export default function NewsPanel({
  ticker,
  maxItems = 8,
  compact = false,
}: {
  ticker: string;
  maxItems?: number;
  compact?: boolean;
}) {
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!ticker) return;

    setLoading(true);
    setError(false);

    fetch(`/api/news?ticker=${encodeURIComponent(ticker)}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        if (Array.isArray(data)) {
          setNews(data.slice(0, maxItems));
        } else {
          setNews([]);
        }
      })
      .catch(() => {
        setError(true);
        setNews([]);
      })
      .finally(() => setLoading(false));
  }, [ticker, maxItems]);

  if (compact) {
    return (
      <div className="rounded border border-gray-800/60 bg-[#13131a] p-5">
        <h3 className="text-sm font-semibold text-gray-400 mb-4">Market News</h3>
        {loading ? (
          <NewsSkeleton />
        ) : error || news.length === 0 ? (
          <p className="text-xs text-gray-600">No news available</p>
        ) : (
          <ul className="space-y-2.5">
            {news.map((item, i) => (
              <li key={i}>
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group block"
                >
                  <p className="text-xs text-gray-300 group-hover:text-white transition-colors line-clamp-2 leading-relaxed">
                    {item.title}
                  </p>
                  <p className="text-[10px] text-gray-600 mt-0.5">
                    {displayDomain(item.url) || item.source}
                    {item.publishedAt && (
                      <> · {timeAgo(item.publishedAt)}</>
                    )}
                  </p>
                </a>
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  return (
    <section className="rounded border border-gray-800/60 bg-[#13131a] p-6">
      <h2 className="text-sm font-semibold text-gray-400 mb-4">
        Recent News
      </h2>

      {loading ? (
        <NewsSkeleton />
      ) : error || news.length === 0 ? (
        <p className="text-xs text-gray-600">No news available for {ticker}</p>
      ) : (
        <ul className="space-y-3">
          {news.map((item, i) => (
            <li
              key={i}
              className="group"
            >
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block hover:bg-gray-900/30 rounded -mx-2 px-2 py-1.5 transition-colors"
              >
                <div className="flex items-start gap-2">
                  {item.sentiment && (
                    <div className="flex-shrink-0 pt-0.5">
                      <SentimentBadge sentiment={item.sentiment} />
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-300 group-hover:text-white transition-colors line-clamp-2 leading-snug">
                      {item.title}
                    </p>
                    <p className="text-[11px] text-gray-600 mt-1">
                      {displayDomain(item.url) || item.source}
                      {item.publishedAt && (
                        <> · {timeAgo(item.publishedAt)}</>
                      )}
                    </p>
                  </div>
                </div>
              </a>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
