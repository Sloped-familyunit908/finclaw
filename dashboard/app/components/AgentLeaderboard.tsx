import { AGENT_REPUTATIONS } from "@/app/lib/mockData";

export default function AgentLeaderboard() {
  const eloStars = (elo: number) =>
    "⭐".repeat(Math.min(5, Math.max(1, Math.floor(elo / 260))));

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">🏅 Agent Reputation Leaderboard</h2>
      <div className="grid gap-3">
        {AGENT_REPUTATIONS.map((a, i) => (
          <div
            key={a.name}
            className="flex items-center gap-3 sm:gap-4 p-3 sm:p-4 rounded-xl border border-gray-800/50 bg-[#13131a] hover:border-orange-800/30 transition-all"
          >
            <div className="text-xl sm:text-2xl w-6 sm:w-8 text-center font-bold text-gray-500">
              #{i + 1}
            </div>
            <div className="text-2xl sm:text-3xl">{a.avatar}</div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-bold text-gray-100">{a.name}</span>
                <span className="text-xs text-gray-500 hidden sm:inline">
                  {a.specialty}
                </span>
              </div>
              <div className="text-xs text-gray-500 mt-0.5">
                {a.correctPredictions}/{a.totalPredictions} correct · Weight{" "}
                {a.debateWeight.toFixed(2)}x
              </div>
            </div>
            <div className="text-right">
              <div className="text-lg sm:text-xl font-bold font-mono text-white">
                {a.elo}
              </div>
              <div className="text-xs text-gray-500">ELO</div>
            </div>
            <div className="text-right w-14 sm:w-20">
              <div
                className={`text-base sm:text-lg font-bold font-mono ${
                  a.accuracy >= 0.8
                    ? "text-green-400"
                    : a.accuracy >= 0.5
                      ? "text-yellow-400"
                      : "text-red-400"
                }`}
              >
                {(a.accuracy * 100).toFixed(0)}%
              </div>
              <div className="text-[10px]">{eloStars(a.elo)}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
