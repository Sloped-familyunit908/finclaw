import { STRATEGIES } from "@/app/lib/mockData";

export default function StrategyGallery() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="text-xl font-bold">📦 Strategy Marketplace</h2>
        <span className="text-xs text-gray-500">
          {STRATEGIES.length} strategies available
        </span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {STRATEGIES.map((name) => {
          const labels: Record<
            string,
            { diff: string; color: string }
          > = {
            "dca-smart": {
              diff: "Beginner",
              color:
                "text-green-400 bg-green-950/40 border-green-800/40",
            },
            "rsi-mean-reversion": {
              diff: "Beginner",
              color:
                "text-green-400 bg-green-950/40 border-green-800/40",
            },
            "golden-cross-momentum": {
              diff: "Intermediate",
              color:
                "text-yellow-400 bg-yellow-950/40 border-yellow-800/40",
            },
            "bollinger-squeeze": {
              diff: "Intermediate",
              color:
                "text-yellow-400 bg-yellow-950/40 border-yellow-800/40",
            },
            "macd-divergence": {
              diff: "Intermediate",
              color:
                "text-yellow-400 bg-yellow-950/40 border-yellow-800/40",
            },
            "grid-trading": {
              diff: "Intermediate",
              color:
                "text-yellow-400 bg-yellow-950/40 border-yellow-800/40",
            },
            "multi-timeframe-trend": {
              diff: "Advanced",
              color:
                "text-orange-400 bg-orange-950/40 border-orange-800/40",
            },
            "volume-profile-breakout": {
              diff: "Advanced",
              color:
                "text-orange-400 bg-orange-950/40 border-orange-800/40",
            },
            "ai-sentiment-reversal": {
              diff: "Expert",
              color:
                "text-red-400 bg-red-950/40 border-red-800/40",
            },
          };
          const l = labels[name] ?? {
            diff: "—",
            color:
              "text-gray-400 bg-gray-800/40 border-gray-700/40",
          };
          const displayName = name
            .split("-")
            .map((w) => w[0].toUpperCase() + w.slice(1))
            .join(" ");

          return (
            <div
              key={name}
              className="p-4 rounded-xl border border-gray-800/50 bg-[#13131a] hover:border-orange-800/40 transition-all group cursor-pointer"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium text-sm text-gray-200">
                  {displayName}
                </span>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-medium border ${l.color}`}
                >
                  {l.diff}
                </span>
              </div>
              <div className="text-xs text-gray-500 font-mono">
                {name}.yaml
              </div>
              <div className="mt-3 flex gap-1.5">
                <span className="px-2 py-0.5 bg-gray-800/50 text-gray-400 text-[10px] rounded">
                  crypto
                </span>
                <span className="px-2 py-0.5 bg-gray-800/50 text-gray-400 text-[10px] rounded">
                  YAML
                </span>
              </div>
              <div className="mt-3 text-xs text-orange-400 opacity-0 group-hover:opacity-100 transition-opacity">
                finclaw install {name} →
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
