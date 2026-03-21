// finclaw.config.example.ts — Configuration template
// Copy this file to finclaw.config.ts and customize
//
// For the LLM API key, create a .env.local file in this directory:
//   FINCLAW_LLM_API_KEY=sk-your-key-here

export default {
  llm: {
    // Provider name (for display only — all providers use OpenAI-compatible API)
    // Supported: 'openai' | 'anthropic' | 'deepseek' | 'groq' | 'ollama' | 'custom'
    provider: 'openai' as const,

    // Model identifier — use your provider's latest model
    // OpenAI:    'gpt-4.1' (latest, 2025), 'gpt-4.1-mini', 'gpt-4.1-nano', 'gpt-4o'
    // Anthropic: 'claude-sonnet-4-20250514' (latest), 'claude-3.5-sonnet-20241022'
    // DeepSeek:  'deepseek-chat', 'deepseek-reasoner'
    // Google:    'gemini-2.5-pro', 'gemini-2.5-flash'
    // Groq:      'llama-3.3-70b-versatile', 'mixtral-8x7b-32768'
    // Ollama:    'llama3.3', 'qwen2.5', 'deepseek-r1'
    model: 'gpt-4.1-mini',

    // Base URL for the API — change for non-OpenAI providers
    // OpenAI:    'https://api.openai.com/v1'
    // Anthropic: 'https://api.anthropic.com/v1' (needs compatible proxy)
    // DeepSeek:  'https://api.deepseek.com/v1'
    // Google:    'https://generativelanguage.googleapis.com/v1beta/openai'
    // Groq:      'https://api.groq.com/openai/v1'
    // Ollama:    'http://localhost:11434/v1'
    baseUrl: 'https://api.openai.com/v1',
  },

  // Default tickers shown in the watchlist
  defaultWatchlist: ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'BTC', 'ETH'],

  // Data refresh interval in seconds
  refreshInterval: 60,
}
