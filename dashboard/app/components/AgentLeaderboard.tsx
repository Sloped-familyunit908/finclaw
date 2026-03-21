export default function AgentLeaderboard() {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-gray-200">
        Agent Performance
      </h2>

      <div className="rounded border border-gray-800/50 bg-[#13131a] p-8 text-center">
        <div className="max-w-md mx-auto space-y-4">
          <div className="w-12 h-12 mx-auto rounded-full bg-gray-800/60 border border-gray-700/50 flex items-center justify-center">
            <svg
              className="w-6 h-6 text-gray-500"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z"
              />
            </svg>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-gray-300">
              No Agent Data Available
            </h3>
            <p className="text-xs text-gray-500 mt-1.5 leading-relaxed">
              Agent reputation metrics are populated when you run multi-agent
              analysis via the FinClaw CLI. Agents earn ELO ratings and
              accuracy scores based on real debate outcomes.
            </p>
          </div>

          <div className="bg-gray-900/60 border border-gray-700/40 rounded-md p-4 text-left">
            <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-2 font-semibold">
              Get Started
            </p>
            <code className="text-xs text-teal-400 font-mono block leading-relaxed">
              $ finclaw debate BTC --agents 3
            </code>
            <p className="text-[10px] text-gray-600 mt-2">
              Run multiple debates to build agent track records and ELO ratings.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
