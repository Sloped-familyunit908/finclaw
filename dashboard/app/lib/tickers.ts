/* ════════════════════════════════════════════════════════════════
   TICKER DATABASE — FinClaw
   Built-in ticker list for search and watchlist type-ahead.
   ════════════════════════════════════════════════════════════════ */

export interface TickerInfo {
  symbol: string;
  name: string;
  nameCn?: string;
  market: "US" | "CN" | "Crypto";
}

/* ── Top 50 US Stocks ── */
export const US_TICKER_LIST: TickerInfo[] = [
  { symbol: "AAPL", name: "Apple Inc", market: "US" },
  { symbol: "MSFT", name: "Microsoft Corp", market: "US" },
  { symbol: "NVDA", name: "NVIDIA Corp", market: "US" },
  { symbol: "GOOGL", name: "Alphabet Inc", market: "US" },
  { symbol: "AMZN", name: "Amazon.com Inc", market: "US" },
  { symbol: "META", name: "Meta Platforms Inc", market: "US" },
  { symbol: "TSLA", name: "Tesla Inc", market: "US" },
  { symbol: "BRK.B", name: "Berkshire Hathaway", market: "US" },
  { symbol: "AVGO", name: "Broadcom Inc", market: "US" },
  { symbol: "JPM", name: "JPMorgan Chase", market: "US" },
  { symbol: "LLY", name: "Eli Lilly & Co", market: "US" },
  { symbol: "V", name: "Visa Inc", market: "US" },
  { symbol: "UNH", name: "UnitedHealth Group", market: "US" },
  { symbol: "XOM", name: "Exxon Mobil Corp", market: "US" },
  { symbol: "MA", name: "Mastercard Inc", market: "US" },
  { symbol: "COST", name: "Costco Wholesale", market: "US" },
  { symbol: "HD", name: "Home Depot Inc", market: "US" },
  { symbol: "PG", name: "Procter & Gamble", market: "US" },
  { symbol: "JNJ", name: "Johnson & Johnson", market: "US" },
  { symbol: "ABBV", name: "AbbVie Inc", market: "US" },
  { symbol: "WMT", name: "Walmart Inc", market: "US" },
  { symbol: "NFLX", name: "Netflix Inc", market: "US" },
  { symbol: "BAC", name: "Bank of America", market: "US" },
  { symbol: "CRM", name: "Salesforce Inc", market: "US" },
  { symbol: "AMD", name: "Advanced Micro Devices", market: "US" },
  { symbol: "ORCL", name: "Oracle Corp", market: "US" },
  { symbol: "TMO", name: "Thermo Fisher Scientific", market: "US" },
  { symbol: "CSCO", name: "Cisco Systems", market: "US" },
  { symbol: "ACN", name: "Accenture plc", market: "US" },
  { symbol: "MRK", name: "Merck & Co", market: "US" },
  { symbol: "PEP", name: "PepsiCo Inc", market: "US" },
  { symbol: "LIN", name: "Linde plc", market: "US" },
  { symbol: "ADBE", name: "Adobe Inc", market: "US" },
  { symbol: "ABT", name: "Abbott Laboratories", market: "US" },
  { symbol: "KO", name: "Coca-Cola Co", market: "US" },
  { symbol: "INTC", name: "Intel Corp", market: "US" },
  { symbol: "DIS", name: "Walt Disney Co", market: "US" },
  { symbol: "QCOM", name: "Qualcomm Inc", market: "US" },
  { symbol: "INTU", name: "Intuit Inc", market: "US" },
  { symbol: "TXN", name: "Texas Instruments", market: "US" },
  { symbol: "CMCSA", name: "Comcast Corp", market: "US" },
  { symbol: "PM", name: "Philip Morris Intl", market: "US" },
  { symbol: "NKE", name: "Nike Inc", market: "US" },
  { symbol: "IBM", name: "IBM Corp", market: "US" },
  { symbol: "GE", name: "GE Aerospace", market: "US" },
  { symbol: "NOW", name: "ServiceNow Inc", market: "US" },
  { symbol: "ISRG", name: "Intuitive Surgical", market: "US" },
  { symbol: "UBER", name: "Uber Technologies", market: "US" },
  { symbol: "GS", name: "Goldman Sachs", market: "US" },
  { symbol: "PLTR", name: "Palantir Technologies", market: "US" },
];

/* ── Top 30 A-Share Stocks ── */
export const CN_TICKER_LIST: TickerInfo[] = [
  { symbol: "600519.SH", name: "Kweichow Moutai", nameCn: "贵州茅台", market: "CN" },
  { symbol: "300750.SZ", name: "CATL", nameCn: "宁德时代", market: "CN" },
  { symbol: "601318.SH", name: "Ping An Insurance", nameCn: "中国平安", market: "CN" },
  { symbol: "600036.SH", name: "China Merchants Bank", nameCn: "招商银行", market: "CN" },
  { symbol: "601899.SH", name: "Zijin Mining", nameCn: "紫金矿业", market: "CN" },
  { symbol: "600438.SH", name: "Tongwei Co", nameCn: "通威股份", market: "CN" },
  { symbol: "000858.SZ", name: "Wuliangye Yibin", nameCn: "五粮液", market: "CN" },
  { symbol: "002415.SZ", name: "Hikvision", nameCn: "海康威视", market: "CN" },
  { symbol: "600900.SH", name: "Yangtze Power", nameCn: "长江电力", market: "CN" },
  { symbol: "601012.SH", name: "LONGi Green Energy", nameCn: "隆基绿能", market: "CN" },
  { symbol: "000625.SZ", name: "Changan Auto", nameCn: "长安汽车", market: "CN" },
  { symbol: "000988.SZ", name: "Huagong Tech", nameCn: "华工科技", market: "CN" },
  { symbol: "600276.SH", name: "Jiangsu Hengrui", nameCn: "恒瑞医药", market: "CN" },
  { symbol: "002594.SZ", name: "BYD", nameCn: "比亚迪", market: "CN" },
  { symbol: "601398.SH", name: "ICBC", nameCn: "工商银行", market: "CN" },
  { symbol: "600030.SH", name: "CITIC Securities", nameCn: "中信证券", market: "CN" },
  { symbol: "000333.SZ", name: "Midea Group", nameCn: "美的集团", market: "CN" },
  { symbol: "002230.SZ", name: "iFlytek", nameCn: "科大讯飞", market: "CN" },
  { symbol: "601688.SH", name: "Huatai Securities", nameCn: "华泰证券", market: "CN" },
  { symbol: "688981.SH", name: "SMIC", nameCn: "中芯国际", market: "CN" },
  { symbol: "603259.SH", name: "WuXi AppTec", nameCn: "药明康德", market: "CN" },
  { symbol: "000001.SZ", name: "Ping An Bank", nameCn: "平安银行", market: "CN" },
  { symbol: "600887.SH", name: "Yili Industrial", nameCn: "伊利股份", market: "CN" },
  { symbol: "601888.SH", name: "China Tourism Group", nameCn: "中国中免", market: "CN" },
  { symbol: "300059.SZ", name: "East Money", nameCn: "东方财富", market: "CN" },
  { symbol: "002475.SZ", name: "Luxshare Precision", nameCn: "立讯精密", market: "CN" },
  { symbol: "600809.SH", name: "Shanxi Fenjiu", nameCn: "山西汾酒", market: "CN" },
  { symbol: "002714.SZ", name: "Muyuan Foods", nameCn: "牧原股份", market: "CN" },
  { symbol: "601919.SH", name: "COSCO Shipping", nameCn: "中远海控", market: "CN" },
  { symbol: "600050.SH", name: "China Unicom", nameCn: "中国联通", market: "CN" },
];

/* ── Top 10 Crypto ── */
export const CRYPTO_TICKER_LIST: TickerInfo[] = [
  { symbol: "BTC", name: "Bitcoin", market: "Crypto" },
  { symbol: "ETH", name: "Ethereum", market: "Crypto" },
  { symbol: "SOL", name: "Solana", market: "Crypto" },
  { symbol: "BNB", name: "BNB", market: "Crypto" },
  { symbol: "XRP", name: "Ripple", market: "Crypto" },
  { symbol: "ADA", name: "Cardano", market: "Crypto" },
  { symbol: "DOGE", name: "Dogecoin", market: "Crypto" },
  { symbol: "DOT", name: "Polkadot", market: "Crypto" },
  { symbol: "AVAX", name: "Avalanche", market: "Crypto" },
  { symbol: "LINK", name: "Chainlink", market: "Crypto" },
];

/* ── Combined list for search ── */
export const ALL_TICKERS: TickerInfo[] = [
  ...US_TICKER_LIST,
  ...CN_TICKER_LIST,
  ...CRYPTO_TICKER_LIST,
];

/* ── Search function: match on symbol, name, or nameCn ── */
export function searchTickers(query: string, limit = 8): TickerInfo[] {
  if (!query.trim()) return [];
  const q = query.trim().toLowerCase();
  const results: TickerInfo[] = [];

  for (const ticker of ALL_TICKERS) {
    if (results.length >= limit) break;
    if (
      ticker.symbol.toLowerCase().includes(q) ||
      ticker.name.toLowerCase().includes(q) ||
      (ticker.nameCn && ticker.nameCn.includes(q))
    ) {
      results.push(ticker);
    }
  }

  return results;
}

/* ── Lookup a ticker by symbol ── */
export function findTicker(symbol: string): TickerInfo | undefined {
  return ALL_TICKERS.find(
    (t) => t.symbol.toLowerCase() === symbol.toLowerCase()
  );
}
