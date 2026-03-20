/* ════════════════════════════════════════════════════════════════
   UTILITY FUNCTIONS — FinClaw 🦀📈
   ════════════════════════════════════════════════════════════════ */

export const fmt = {
  usd: (n: number, d = 0) =>
    "$" + n.toLocaleString(undefined, { maximumFractionDigits: d }),

  cny: (n: number, d = 2) =>
    "¥" + n.toLocaleString(undefined, { maximumFractionDigits: d }),

  pct: (n: number, d = 2) =>
    (n >= 0 ? "+" : "") + (n * 100).toFixed(d) + "%",

  pctRaw: (n: number, d = 2) =>
    (n >= 0 ? "+" : "") + n.toFixed(d) + "%",

  compact: (n: number) => {
    if (n >= 1e12) return "$" + (n / 1e12).toFixed(2) + "T";
    if (n >= 1e9) return "$" + (n / 1e9).toFixed(1) + "B";
    if (n >= 1e6) return "$" + (n / 1e6).toFixed(1) + "M";
    return "$" + n.toLocaleString();
  },

  compactCn: (n: number) => {
    if (n >= 1e8) return "¥" + (n / 1e8).toFixed(1) + "亿";
    if (n >= 1e4) return "¥" + (n / 1e4).toFixed(1) + "万";
    return "¥" + n.toLocaleString();
  },
};

/* Agent visual config */
export const AGENTS: Record<string, { avatar: string; color: string; bg: string; gradient: string }> = {
  Warren:   { avatar: "🧓", color: "text-green-400",  bg: "bg-green-950/40 border-green-800/60",   gradient: "from-green-600 to-emerald-600" },
  George:   { avatar: "🌍", color: "text-blue-400",   bg: "bg-blue-950/40 border-blue-800/60",     gradient: "from-blue-600 to-cyan-600" },
  Ada:      { avatar: "📐", color: "text-purple-400", bg: "bg-purple-950/40 border-purple-800/60",  gradient: "from-purple-600 to-violet-600" },
  Sentinel: { avatar: "📡", color: "text-yellow-400", bg: "bg-yellow-950/40 border-yellow-800/60",  gradient: "from-yellow-600 to-amber-600" },
  Guardian: { avatar: "🛡️", color: "text-red-400",    bg: "bg-red-950/40 border-red-800/60",        gradient: "from-red-600 to-rose-600" },
  "Arena Moderator": { avatar: "⚖️", color: "text-cyan-400", bg: "bg-cyan-950/40 border-cyan-800/60", gradient: "from-cyan-600 to-sky-600" },
};

export const SIGNAL_STYLES: Record<string, { text: string; bg: string; border: string }> = {
  strong_buy:  { text: "text-emerald-300", bg: "bg-emerald-950/60", border: "border-emerald-700" },
  buy:         { text: "text-green-300",   bg: "bg-green-950/60",   border: "border-green-700" },
  hold:        { text: "text-gray-300",    bg: "bg-gray-800/60",    border: "border-gray-600" },
  sell:        { text: "text-orange-300",  bg: "bg-orange-950/60",  border: "border-orange-700" },
  strong_sell: { text: "text-red-300",     bg: "bg-red-950/60",     border: "border-red-700" },
};
