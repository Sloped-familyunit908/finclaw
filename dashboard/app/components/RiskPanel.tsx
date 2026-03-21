import { fmt } from "@/app/lib/utils";
import { RISK } from "@/app/lib/fallbackData";

export default function RiskPanel() {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-gray-200">Constitutional Risk Framework</h2>
      <p className="text-xs text-gray-500">
        Immutable rules that cannot be overridden by agent consensus.
      </p>

      <div className="overflow-x-auto rounded border border-gray-800/60">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-900/50 text-gray-400 text-xs uppercase tracking-wider">
              <th className="text-left py-3 px-4">Parameter</th>
              <th className="text-right py-3 px-4">Value</th>
              <th className="text-left py-3 px-4 hidden sm:table-cell">Description</th>
            </tr>
          </thead>
          <tbody>
            {[
              {
                label: "Max Position Size",
                value: fmt.pct(RISK.maxPositionPct, 0),
                desc: "Single position limit",
              },
              {
                label: "Drawdown Halt",
                value: fmt.pct(RISK.maxDrawdownHalt, 0),
                desc: "Emergency halt trigger",
              },
              {
                label: "Daily Loss Limit",
                value: fmt.pct(RISK.maxDailyLoss, 0),
                desc: "Pause trading for the day",
              },
              {
                label: "Min Confidence",
                value: fmt.pct(RISK.minDebateConfidence, 0),
                desc: "Debate must be this confident",
              },
              {
                label: "Min Agents Agree",
                value: RISK.minAgentsAgreeing.toString(),
                desc: "Minimum agents in consensus",
              },
              {
                label: "Max Leverage",
                value: RISK.maxLeverage + "x",
                desc: "No leverage in v1",
              },
            ].map((r, i) => (
              <tr
                key={r.label}
                className={`border-t border-gray-800/30 ${i === 0 ? "" : ""} hover:bg-gray-900/30`}
              >
                <td className="py-2.5 px-4 font-medium text-gray-300">
                  {r.label}
                </td>
                <td className="py-2.5 px-4 text-right font-mono font-bold text-white">
                  {r.value}
                </td>
                <td className="py-2.5 px-4 text-gray-500 text-xs hidden sm:table-cell">
                  {r.desc}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
