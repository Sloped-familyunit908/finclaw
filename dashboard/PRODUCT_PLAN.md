# FinClaw Dashboard — Product Redesign Plan

> Designed as if this were a Google-scale product launch.
> Every feature must earn its place. No bloat, no gimmicks.

## Design Philosophy

**Three principles:**
1. **Data first, AI second** — Show the data fast, use AI to explain it
2. **Zero learning curve** — First-time user gets value in 5 seconds
3. **Progressive disclosure** — Simple by default, powerful when needed

## Product Architecture (Target State)

```
┌─────────────────────────────────────────────────────────────────┐
│ FinClaw                                     [Search: AAPL...]  │
│ S&P 500 5,234 +0.8% │ Nasdaq 16,420 +1.2% │ BTC 70,732 +0.7% │
├─────────────────────────────────────────────────────────────────┤
│ [Dashboard] [Screener] [Backtest] [Settings]                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Dashboard tab (default):                                       │
│  ┌──────────────────────────────────┐ ┌───────────────────────┐│
│  │ Watchlist (sortable table)       │ │ Sector Heatmap        ││
│  │ AAPL  $248  -0.4%  $88M  ▁▂▃▅▇ │ │ [treemap viz]         ││
│  │ NVDA  $173  -3.3%  $210M ▇▅▃▂▁ │ │                       ││
│  │ BTC   $70K  +0.7%  $36B  ▃▃▄▅▅ │ │                       ││
│  │ 通威   ¥18   +2.0%  ¥16亿 ▁▂▃▅▆ │ │                       ││
│  │ [+ Add ticker]                   │ │                       ││
│  └──────────────────────────────────┘ └───────────────────────┘│
│  ┌──────────────────────────────────┐ ┌───────────────────────┐│
│  │ Top Movers               Today  │ │ Recent News (AI)      ││
│  │ ▲ 长安汽车  +3.4%               │ │ NVDA earnings beat... ││
│  │ ▲ 中芯国际  +4.2%               │ │ Fed holds rates...    ││
│  │ ▼ 宁德时代  -0.5%               │ │ BTC breaks $70K...    ││
│  └──────────────────────────────────┘ └───────────────────────┘│
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ AI Assistant                                     [Expand ↑]││
│  │ Ask anything: "Compare AAPL vs MSFT" / "低PE半导体股"       ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## Feature Prioritization Matrix

Scoring: Impact(1-5) × Feasibility(1-5) ÷ Effort(1-5)

| Feature | Impact | Feasibility | Effort | Score | Phase |
|---------|--------|-------------|--------|-------|-------|
| AI Chat Assistant | 5 | 4 | 3 | 6.7 | **1** |
| Watchlist CRUD | 5 | 5 | 2 | 12.5 | **1** |
| Search (functional) | 4 | 5 | 1 | 20 | **1** |
| News + AI Summary | 4 | 4 | 3 | 5.3 | **1** |
| Screener UI | 4 | 4 | 3 | 5.3 | **1** |
| Sector Heatmap | 3 | 4 | 2 | 6.0 | **2** |
| Top Movers widget | 3 | 5 | 1 | 15 | **1** |
| Time range selector | 3 | 5 | 2 | 7.5 | **1** |
| Fundamental data | 4 | 3 | 3 | 4.0 | **2** |
| Portfolio tracker | 3 | 3 | 3 | 3.0 | **2** |
| Keyboard shortcuts | 2 | 5 | 2 | 5.0 | **3** |
| Multi-panel layout | 2 | 2 | 4 | 1.0 | **3** |
| Light/dark toggle | 1 | 5 | 1 | 5.0 | **3** |

## Phase 1: "Make it useful" (this sprint)

### 1.1 AI Chat Assistant (bottom bar)
- Persistent bottom bar: "Ask anything about markets..."
- Expand into a right-side panel when active
- Vercel AI SDK streamUI() for Generative UI
- Tools the LLM can call:
  - `showStockPrice(ticker)` → Price card component
  - `compareStocks(ticker1, ticker2)` → Side-by-side component
  - `screenStocks(criteria)` → Results table component
  - `analyzeStock(ticker)` → Full analysis component
  - `showNews(ticker)` → News list component
- No API key → show "Configure LLM in finclaw.config.ts"
- Has API key → full functionality

### 1.2 Watchlist with Add/Remove
- "+" button to add any ticker
- Type-ahead search
- Save to localStorage
- Drag to reorder
- Default: AAPL, NVDA, TSLA, BTC, ETH (or from config)

### 1.3 Functional Search
- Global search in header
- As-you-type results dropdown
- Searches: tickers, company names, Chinese names
- Enter → navigate to /stock/[code]

### 1.4 News + AI Summary
- `/api/news?ticker=AAPL` route
- Source: Finnhub free API or RSS feeds
- On detail page: recent 5 news items
- If LLM configured: one-line AI summary + sentiment badge
- If no LLM: just headlines with source links

### 1.5 Top Movers Widget
- Homepage widget showing today's biggest gainers/losers
- From existing price data (sort by change%)
- Compact list, 5 up + 5 down

### 1.6 Time Range Selector (detail page)
- Buttons: 1W / 1M / 3M / 6M / 1Y / All
- Changes the history API range
- TradingView chart updates accordingly

## Phase 2: "Make it powerful" (next sprint)

### 2.1 Screener UI
- Multi-filter interface
- Basic filters: Price, Change%, Volume, Market Cap
- Advanced: PE, RSI, MACD signal, Sector
- AI-enhanced: natural language input bar
- Sort by any column

### 2.2 Sector Heatmap
- Treemap visualization (d3-treemap or lightweight lib)
- Size = market cap, Color = daily change
- Click sector → drill into stocks

### 2.3 Fundamental Data on Detail Page
- Key stats: PE, PB, ROE, Debt/Equity, Revenue Growth
- Source: Yahoo Finance / Eastmoney API
- Simple table format, no fancy charts

### 2.4 Portfolio UI
- Add positions (ticker, shares, cost basis)
- Auto-calculate P&L, weights
- Save to localStorage
- If LLM: "Analyze my portfolio risk"

## Phase 3: "Make it delightful" (polish)

### 3.1 Keyboard Shortcuts
- / → focus search
- j/k → navigate watchlist
- Enter → open stock detail
- Esc → back to dashboard

### 3.2 Light/Dark Toggle
- Default dark (finance standard)
- Light mode option

### 3.3 Customizable Layout
- Drag-and-drop widgets
- Save layout preference

## Technical Architecture

```
app/
  page.tsx                    — Dashboard (watchlist + widgets)
  stock/[code]/page.tsx       — Stock detail
  screener/page.tsx           — NEW: Screener
  settings/page.tsx           — NEW: Settings (optional)
  
  api/
    prices/route.ts           — Real-time quotes
    history/route.ts          — OHLCV history  
    indices/route.ts          — Market indices
    news/route.ts             — NEW: News aggregation
    screener/route.ts         — NEW: Stock screening
    chat/route.ts             — NEW: AI chat (Vercel AI SDK)
    
  components/
    Header.tsx                — Nav + search
    MarketIndexBanner.tsx     — Index ticker bar
    WatchlistTable.tsx        — NEW: Sortable watchlist with CRUD
    PriceCard.tsx             — Compact price card
    TopMovers.tsx             — NEW: Gainers/losers widget
    SectorHeatmap.tsx         — NEW: Treemap (Phase 2)
    NewsPanel.tsx             — NEW: News + AI summary
    ChatAssistant.tsx         — NEW: AI chat panel
    StockChart.tsx            — NEW: TradingView chart (extracted)
    TimeRangeSelector.tsx     — NEW: 1W/1M/3M/1Y buttons
    
  lib/
    config.ts                 — NEW: finclaw.config.ts loader
    chat-tools.ts             — NEW: AI tool definitions
    indicators.ts             — Technical indicator calculations
    fallbackData.ts           — Fallback/default data

finclaw.config.ts             — NEW: User configuration
.env.local                    — API keys (gitignored)
```

## Key Design Decisions

1. **AI is enhancement, not requirement** — Everything works without LLM. AI features appear only when configured.

2. **No separate "AI" tab** — AI is integrated everywhere (chat bar, news summaries, screener NL input). It should feel natural, not bolted on.

3. **Reduce tabs, increase widgets** — Instead of 7 tabs, have 3-4 tabs with widget-based layouts within each.

4. **Mobile-first won't work** — This is a desktop power tool. Mobile can be a simplified view later.

5. **Open source advantage** — Users can add their own data sources, AI providers, and custom widgets. finclaw.config.ts is the extension point.
