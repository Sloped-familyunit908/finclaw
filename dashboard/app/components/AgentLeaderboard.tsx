import { AGENT_REPUTATIONS } from "@/app/lib/mockData";

export default function AgentLeaderboard() {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-gray-200">Agent Reputation Leaderboard</h2>
      <div className="overflow-x-auto rounded border border-gray-800/60">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-900/50 text-gray-400 text-xs uppercase tracking-wider">
              <th className="text-center py-3 px-3 w-12">Rank</th>
              <th className="text-left py-3 px-3">Agent</th>
              <th className="text-left py-3 px-3 hidden sm:table-cell">Specialty</th>
              <th className="text-right py-3 px-3">ELO</th>
              <th className="text-right py-3 px-3">Accuracy</th>
              <th className="text-right py-3 px-3 hidden md:table-cell">Record</th>
              <th className="text-right py-3 px-3 hidden md:table-cell">Weight</th>
            </tr>
          </thead>
          <tbody>
            {AGENT_REPUTATIONS.map((a, i) => (
              <tr
                key={a.name}
                className={`border-t border-gray-800/30 ${
                  i === 0 ? "bg-gray-800/20" : "hover:bg-gray-900/30"
                }`}
              >
                <td className="py-2.5 px-3 text-center font-mono text-gray-500">
                  {i + 1}
                </td>
                <td className="py-2.5 px-3">
                  <span className="font-medium text-gray-100">{a.name}</span>
                </td>
                <td className="py-2.5 px-3 text-gray-500 text-xs hidden sm:table-cell">
                  {a.specialty}
                </td>
                <td className="py-2.5 px-3 text-right font-mono font-bold text-white">
                  {a.elo}
                </td>
                <td className="py-2.5 px-3 text-right">
                  <span
                    className={`font-mono font-bold ${
                      a.accuracy >= 0.8
                        ? "text-green-400"
                        : a.accuracy >= 0.5
                          ? "text-yellow-400"
                          : "text-red-400"
                    }`}
                  >
                    {(a.accuracy * 100).toFixed(0)}%
                  </span>
                </td>
                <td className="py-2.5 px-3 text-right font-mono text-gray-400 text-xs hidden md:table-cell">
                  {a.correctPredictions}/{a.totalPredictions}
                </td>
                <td className="py-2.5 px-3 text-right font-mono text-gray-400 hidden md:table-cell">
                  {a.debateWeight.toFixed(2)}x
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
