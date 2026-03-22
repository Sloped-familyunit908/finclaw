// finclaw.config.example.ts — Configuration template
// Copy this file to finclaw.config.ts and customize
//
// API keys go in .env.local (never committed to git):
//   FINCLAW_LLM_API_KEY=sk-your-key-here
//   FINCLAW_LLM_BASE_URL=https://api.openai.com/v1
//   FINCLAW_LLM_MODEL=gpt-4.1-mini

export default {
  // --- LLM Configuration (for AI Chat) ---
  llm: {
    // Provider: 'openai' | 'anthropic' | 'deepseek' | 'groq' | 'ollama' | 'custom'
    provider: 'openai' as const,

    // Model — use your provider's latest
    // OpenAI:    'gpt-4.1', 'gpt-4.1-mini'
    // Anthropic: 'claude-sonnet-4'
    // DeepSeek:  'deepseek-chat', 'deepseek-reasoner'
    // Google:    'gemini-2.5-pro', 'gemini-2.5-flash'
    // Groq:      'llama-3.3-70b-versatile'
    // Ollama:    'llama3.3', 'qwen2.5'
    model: 'gpt-4.1-mini',

    // API base URL — change for non-OpenAI providers
    // OpenAI:    'https://api.openai.com/v1'
    // DeepSeek:  'https://api.deepseek.com/v1'
    // Google:    'https://generativelanguage.googleapis.com/v1beta/openai'
    // Groq:      'https://api.groq.com/openai/v1'
    // Ollama:    'http://localhost:11434/v1'
    baseUrl: 'https://api.openai.com/v1',
  },

  // --- Default Watchlist ---
  defaultWatchlist: ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'BTC', 'ETH'],

  // --- Data Refresh ---
  refreshInterval: 60, // seconds
}

// --- Environment Variables (.env.local) ---
//
// Required for AI Chat:
//   FINCLAW_LLM_API_KEY=sk-xxx
//
// Optional overrides:
//   FINCLAW_LLM_BASE_URL=https://api.openai.com/v1
//   FINCLAW_LLM_MODEL=gpt-4.1-mini
//
// --- Features by API key ---
//
// No keys needed:
//   - Real-time prices (US, Crypto, A-shares)
//   - TradingView charts + technical indicators
//   - Stock screener, compare, watchlist
//   - Evolution engine + backtest
//   - Portfolio tracking
//
// With LLM key:
//   - AI Chat assistant
//   - Natural language screener (coming soon)
//   - News sentiment analysis (coming soon)
//
// Fundamental data (PE, ROE, revenue growth) is fetched from
// Yahoo Finance when available. Some endpoints require
// authentication — the dashboard gracefully hides panels
// when data is unavailable.
