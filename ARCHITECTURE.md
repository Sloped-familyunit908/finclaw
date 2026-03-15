# FinClaw 重构计划 — 梁文峰 x Google CTO 视角

## 竞品格局（2026年3月）

| 项目 | Stars | 语言 | 定位 | 弱点 |
|------|-------|------|------|------|
| freqtrade | ~35K | Python | 加密货币交易机器人 | 纯规则策略，无AI，UI老旧 |
| Qlib (微软) | ~16K | Python | AI量化研究平台 | 学术化，不能实盘，无UI |
| nautilus_trader | ~5K | Rust+Python | 生产级交易引擎 | 太复杂，门槛极高，无AI |
| FinRL | ~10K | Python | 强化学习交易 | 纯学术，不能用 |
| ai-hedge-fund | ~48K | Python | AI对冲基金教学 | Demo玩具，不能交易 |
| StockSharp | ~7K | C# | 全品种交易平台 | C#生态小，过于传统 |

## 关键洞察

1. **没有人做到 AI + 实盘 + 好看的UI + 生态** — 这是空白
2. freqtrade 有最大用户群但没AI → 我们的AI能力是杀手锏
3. Qlib 有最强AI但不能交易 → 我们做端到端
4. nautilus 性能最强但没人用得起 → 我们降低门槛
5. ai-hedge-fund stars最多但是Demo → 证明市场需求巨大

## 差异化定位

**FinClaw = freqtrade的易用性 + Qlib的AI能力 + nautilus的性能 + ai-hedge-fund的理念**

一句话：**第一个让普通人用上专业AI量化的开源平台**

---

## 语言决策

### 最终选择：Rust (核心引擎) + Python (策略层) + TypeScript (UI)

理由：
1. **Rust 核心引擎** — 性能、安全、2026年最受欢迎语言，GitHub生态增长最快
2. **Python 策略层** — 量化圈通用语言，降低贡献门槛，无数ML库
3. **TypeScript 前端** — React/Next.js Dashboard，现代开发者标配

这和 nautilus_trader 的架构选择一致，但我们的创新在于：
- nautilus 面向专业交易员 → 我们面向广大开发者和个人投资者
- nautilus 无AI → 我们原生集成AI Agent

### 为什么不全Python？
- 交易引擎需要低延迟
- Rust 生态在2026年爆炸式增长
- 吸引 Rust 开发者社区（最活跃的开源贡献者群体）
- 给项目带来技术壁垒和专业感

### 语言分工
```
whale-trader/
├── engine/        # Rust — 核心引擎 (数据管道/订单管理/回测)
├── strategies/    # Python — 策略编写 (PyO3 bridge)
├── agents/        # Python — AI Agent 层 (LLM调用)
├── dashboard/     # TypeScript — Web UI (Next.js)
└── sdk/           # Python — SDK/CLI
```

---

## 5 大创新点

### 1. 🏟️ Agent Debate Arena（独创）
不是简单的投票，而是 AI Agent 之间的**对抗辩论**：
- 每个Agent独立分析
- 进入辩论场，互相挑战对方的逻辑
- AI仲裁者做最终裁决
- **用户可以观看辩论过程**（这是杀手级UX功能）
- 类似于DeepSeek的"思维链"但是多Agent版本

### 2. 📦 Strategy Marketplace（生态核心）
任何人都可以贡献策略，类似于：
- npm 之于 Node.js
- Docker Hub 之于 Docker
- HuggingFace 之于 ML models

```yaml
# whale-strategy.yaml
name: golden-cross-ai
version: 1.2.0
author: community-user
description: AI-enhanced golden cross strategy
performance:
  sharpe: 2.3
  max_drawdown: -12%
  backtest_period: 2023-2026
tags: [crypto, momentum, ai]
```

```bash
whale install golden-cross-ai
whale backtest golden-cross-ai --asset BTC --period 1y
whale run golden-cross-ai --mode paper
```

### 3. 🧪 Strategy Lab（降低门槛）
**用自然语言描述策略，AI自动生成代码并回测**

```
User: "当RSI低于30且MACD金叉时买入，持仓超过5%利润时卖出"
FinClaw: [自动生成Python策略代码] → [自动回测] → [展示结果]
```

这是 freqtrade 和 Qlib 都没有的功能。

### 4. 🔮 Multi-Modal Analysis（多模态分析）
不只看价格数据：
- 📰 新闻情绪（RSS + AI总结）
- 🐦 社交媒体信号（Twitter/Reddit关键词热度）
- 🔗 链上数据（大户钱包追踪）
- 📊 宏观经济指标
- 🌐 全球事件影响评估

### 5. 🏆 Leaderboard & Social Trading
- 策略排行榜（实时收益率排名）
- 跟单功能（一键跟随Top策略）
- 策略对战（两个策略PK）
- 社区投票最佳策略

---

## UI 设计原则

### 设计语言：Dark Mode + Data Dense + Glassmorphism

参考项目：
- **TradingView** — 图表交互标准
- **Linear** — 极简SaaS美学
- **Vercel Dashboard** — 开发者友好
- **Bloomberg Terminal** — 数据密度

### 核心页面

1. **Dashboard（仪表盘）**
   - 实时P&L曲线
   - 持仓一览（卡片式）
   - Agent信号面板
   - 快速操作按钮

2. **Arena（辩论场）** ← 杀手级功能
   - 实时显示Agent辩论过程
   - 像聊天窗口一样展示
   - 每个Agent有头像和角色
   - 最终裁决动画

3. **Strategy Lab（策略实验室）**
   - 自然语言→代码→回测 三步流程
   - 在线代码编辑器（Monaco Editor）
   - 实时回测结果图表

4. **Marketplace（策略市场）**
   - 策略卡片展示
   - 收益率/风险指标
   - 一键安装/回测

5. **Backtest（回测）**
   - 专业级回测报告
   - Sharpe/Sortino/MaxDD 等指标
   - 可交互的收益曲线

### 技术选型
- **Next.js 14** — App Router + Server Components
- **Tailwind CSS** — 快速迭代
- **shadcn/ui** — 组件库
- **Recharts / Lightweight Charts** — 金融图表
- **Framer Motion** — 动画

---

## 项目路线图

### Phase 1: Foundation（2周）
- [x] 项目架构设计
- [ ] Rust 核心引擎（数据管道 + 订单管理）
- [ ] Python Bridge (PyO3)
- [ ] Paper Trading Engine (Rust)
- [ ] 基础 Agent 框架
- [ ] CLI 工具

### Phase 2: Intelligence（2周）
- [ ] Value Agent + Momentum Agent + Sentiment Agent
- [ ] Debate Arena 机制
- [ ] 多数据源集成
- [ ] 自然语言→策略代码生成

### Phase 3: Dashboard（2周）
- [ ] Next.js Dashboard
- [ ] 实时数据WebSocket
- [ ] Arena 辩论可视化
- [ ] 回测报告页面

### Phase 4: Ecosystem（持续）
- [ ] Strategy Marketplace
- [ ] SDK & 文档
- [ ] Community贡献指南
- [ ] Leaderboard

---

## 成本控制

| 组件 | 月费 | 说明 |
|------|------|------|
| Azure App Service (B1) | $13 | Dashboard 托管 |
| Azure Database for PostgreSQL (Flex B1ms) | $25 | 策略数据/交易记录 |
| AI (Claude) | $0 | 本地tokens |
| CoinGecko API | $0 | 免费tier |
| Vercel (前端) | $0 | 免费tier |
| **总计** | **~$38/月** | 远在 $150 预算内 |
