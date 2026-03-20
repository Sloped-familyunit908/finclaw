import { fmt } from "@/app/lib/utils";
import { RISK } from "@/app/lib/mockData";

export default function RiskPanel() {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">🛡️ Constitutional Risk Framework</h2>
      <p className="text-xs text-gray-500">
        Immutable rules that CANNOT be overridden by debate consensus. Inspired
        by Anthropic Constitutional AI.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {[
          {
            label: "Max Position Size",
            value: fmt.pct(RISK.maxPositionPct, 0),
            desc: "Single position limit",
            icon: "📏",
          },
          {
            label: "Drawdown Halt",
            value: fmt.pct(RISK.maxDrawdownHalt, 0),
            desc: "Emergency halt trigger",
            icon: "🛑",
          },
          {
            label: "Daily Loss Limit",
            value: fmt.pct(RISK.maxDailyLoss, 0),
            desc: "Pause trading for the day",
            icon: "📉",
          },
          {
            label: "Min Confidence",
            value: fmt.pct(RISK.minDebateConfidence, 0),
            desc: "Debate must be this confident",
            icon: "🎯",
          },
          {
            label: "Min Agents Agree",
            value: RISK.minAgentsAgreeing.toString(),
            desc: "Minimum agents in consensus",
            icon: "🤝",
          },
          {
            label: "Max Leverage",
            value: RISK.maxLeverage + "x",
            desc: "No leverage in v1",
            icon: "⚖️",
          },
        ].map((r) => (
          <div
            key={r.label}
            className="p-4 rounded-xl border border-gray-800/50 bg-[#13131a]"
          >
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xl">{r.icon}</span>
              <span className="text-sm font-medium text-gray-300">
                {r.label}
              </span>
            </div>
            <div className="text-2xl font-bold font-mono text-white">
              {r.value}
            </div>
            <div className="text-xs text-gray-500 mt-1">{r.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
