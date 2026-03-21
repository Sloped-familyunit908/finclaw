/* ════════════════════════════════════════════════════════════════
   CONFIG LOADER — FinClaw
   ════════════════════════════════════════════════════════════════ */

export interface FinClawConfig {
  llm?: {
    provider?: string;
    model?: string;
    baseUrl?: string;
  };
  defaultWatchlist?: string[];
  refreshInterval?: number;
}

let _configCache: FinClawConfig | null = null;

/** Load user configuration from finclaw.config.ts (project root) */
export function getConfig(): FinClawConfig {
  if (_configCache) return _configCache;
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    _configCache = require('../../finclaw.config').default;
    return _configCache!;
  } catch {
    _configCache = {};
    return _configCache;
  }
}

/** Check if the LLM API key is configured via environment variable */
export function isLLMConfigured(): boolean {
  return !!process.env.FINCLAW_LLM_API_KEY;
}
