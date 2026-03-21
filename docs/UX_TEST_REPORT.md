# finclaw UX 深度测试报告 v2 (2026-03-18)

## ✅ 工作良好的功能 (20+)

| 命令 | 状态 | 体验评分 |
|------|------|----------|
| `quote AAPL MSFT` | ✅ 价格+涨跌幅正常 | ⭐⭐⭐⭐⭐ |
| `quote BTC-USD ETH-USD` | ✅ 加密货币正常 | ⭐⭐⭐⭐⭐ |
| `quote 0700.HK` | ✅ 港股正常 | ⭐⭐⭐⭐⭐ |
| `analyze --ticker AAPL` | ✅ 技术分析完整 | ⭐⭐⭐⭐⭐ |
| `screen --min-price 100` | ✅ 筛选正常 | ⭐⭐⭐⭐ |
| `gainers / losers` | ✅ 排行正常 | ⭐⭐⭐⭐ |
| `fear-greed` | ✅ 恐贪指数正常 | ⭐⭐⭐⭐⭐ |
| `backtest` (5策略) | ✅ 全部正常 | ⭐⭐⭐⭐⭐ |
| `paper start/buy/portfolio/pnl/dashboard/journal` | ✅ 完整流程 | ⭐⭐⭐⭐ |
| `position-size` | ✅ 仓位计算正常 | ⭐⭐⭐⭐⭐ |
| `demo` | ✅ 完整演示 | ⭐⭐⭐⭐⭐ |
| `doctor` | ✅ 健康检查 | ⭐⭐⭐⭐ |
| `sentiment` | ✅ 修复后正常 | ⭐⭐⭐⭐ |
| `watchlist create/quotes` | ✅ 修复后正常 | ⭐⭐⭐⭐ |
| `news AAPL` | ✅ 新闻正常 | ⭐⭐⭐⭐ |
| `trending` | ✅ 热搜正常 | ⭐⭐⭐⭐ |
| `defi-tvl` | ✅ DeFi数据正常 | ⭐⭐⭐⭐⭐ |
| `yields` | ✅ 收益率正常 | ⭐⭐⭐⭐ |
| `btc-metrics` | ✅ 链上数据正常 | ⭐⭐⭐⭐⭐ |
| `risk --portfolio` | ✅ 风险分析正常 | ⭐⭐⭐⭐⭐ |
| `exchanges` | ✅ 交易所列表 | ⭐⭐⭐⭐ |
| `predict run --ticker` | ✅ 修复后正常 | ⭐⭐⭐ |
| `cache` | ✅ 缓存状态 | ⭐⭐⭐⭐ |
| `scan --rule "rsi<40"` | ✅ 扫描正常 | ⭐⭐⭐⭐ |

## ⚠️ 剩余问题

### Bug: compare 策略名不匹配 (中优先级)
`finclaw compare --strategies sma_cross rsi macd` 报 "Unknown strategy"
compare 命令有自己的策略名集合 (momentum, mean_reversion, trend_following, macd_cross, buy_hold)
跟 backtest 的策略名 (sma_cross, rsi, macd, bollinger, momentum) 完全不同！
用户会很困惑。

### Bug: history 不支持日期范围 (低)
`finclaw history AAPL --start 2024-06-01` 报错 "unrecognized arguments"
history 只支持 --limit 和 --timeframe，没有日期筛选。

### UX: paper sell 不给原因 (低)
`paper sell GOOGL 10` 只说 "Order rejected" 不告诉你为什么（没持仓/余额不足）

### UX: paper buy 负数不给提示 (低)
`paper buy AAPL -5` 只说 "Order rejected" 不说原因

### UX: 不存在的策略静默回退 (中)
`backtest --strategy nonexistent` 不报错，静默用默认策略，用户以为在用自己的策略

### UX: history 日期显示为 unix timestamp (低)
history 显示 `1771511400000` 而不是人类可读日期

### 非问题（正常行为）
- 拼错命令 → 显示帮助 ✅
- 不存在的 ticker → 清晰报错 ✅  
- 错误日期格式 → 合理报错 ✅
- 超出资金买入 → 拒绝 ✅
- 无持仓卖出 → 拒绝 ✅
