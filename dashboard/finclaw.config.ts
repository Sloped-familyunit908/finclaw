// finclaw.config.ts — User configuration
// Copy finclaw.config.example.ts and customize

export default {
  llm: {
    provider: 'openai' as const,
    model: 'gpt-4o-mini',
    baseUrl: 'https://api.openai.com/v1',
    // API key should be in .env.local: FINCLAW_LLM_API_KEY=sk-xxx
  },
  defaultWatchlist: ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'BTC', 'ETH'],
  refreshInterval: 60,
}
