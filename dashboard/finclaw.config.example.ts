// finclaw.config.example.ts — Configuration template
// Copy this file to finclaw.config.ts and customize
//
// For the LLM API key, create a .env.local file in this directory:
//   FINCLAW_LLM_API_KEY=sk-your-key-here

export default {
  llm: {
    // Provider name (for display only — all providers use OpenAI-compatible API)
    // Supported: 'openai' | 'anthropic' | 'deepseek' | 'groq' | 'ollama'
    provider: 'openai' as const,

    // Model identifier — must match your provider's model names
    // OpenAI: 'gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'
    // Anthropic: 'claude-3.5-sonnet' (via compatible proxy)
    // DeepSeek: 'deepseek-chat', 'deepseek-reasoner'
    // Ollama: 'llama3', 'mistral', etc.
    model: 'gpt-4o-mini',

    // Base URL for the API — change for non-OpenAI providers
    // OpenAI:   'https://api.openai.com/v1'
    // DeepSeek: 'https://api.deepseek.com/v1'
    // Ollama:   'http://localhost:11434/v1'
    baseUrl: 'https://api.openai.com/v1',
  },

  // Default tickers shown in the watchlist
  defaultWatchlist: ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'BTC', 'ETH'],

  // Data refresh interval in seconds
  refreshInterval: 60,
}
