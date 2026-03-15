# 竞品分析 + 自我反思

## 为什么还没有超过 AHF？

### 1. 我们的"AHF"不是真正的AHF

我们 benchmark 里的 `benchmark_avg(h, "selective", 7)` 只是一个**随机入场模拟器**：
- 7% 概率随机入场
- 持有 3-20 bars（随机）
- -5% 止损
- 跑7个seed取平均

**这不是 ai-hedge-fund 的真实策略！**

### 2. 真正的 AHF 架构

AHF 使用**17个AI agent的集体智慧**：
- 12个投资大师人格（Buffett, Druckenmiller, Cathie Wood 等）
- Technical Analyst（5策略加权投票）
- Fundamentals Analyst（财报分析）
- Sentiment Analyst（市场情绪）
- Risk Manager + Portfolio Manager

**核心差异**：AHF 用 LLM 推理来综合多种信号，我们用 if/elif 硬编码规则。

### 3. AHF Technical Analyst 的具体实现

```
信号组合权重：
- Trend Following: 25%  (EMA 8/21/55 + ADX)
- Mean Reversion: 20%   (z-score 50MA + Bollinger Bands + RSI 14/28)
- Momentum: 25%         (1M/3M/6M 加权 + Volume confirmation)
- Volatility: 15%       (Vol regime via 63MA + Vol z-score)
- Stat Arb: 15%         (Price distribution statistics)
```

### 4. 为什么我们在某些场景超过AHF

我们赢AHF的5个场景（AAPL, META, INTC, CATL, CSI300）有共同特征：
- **防守型场景**（bear/correction）→ 我们的 regime detection + 小仓位 + 止损比AHF的"随机模拟"好
- **高波动场景** → 我们的 trailing stop 系统比随机持有更好

### 5. 为什么AHF在7个场景超过我们

AHF赢的场景：NVDA, TSLA, AMZN, Moutai, BTC, ETH, SOL
- **趋势跟随场景** → AHF的模拟（随机入场）在强趋势中等价于 partial B&H
- **Crypto** → AHF 模拟的随机入场+随机持有在高波动+趋势中有幸运优势
- **但真实AHF完全不同** → 它用 LLM+fundamentals+sentiment，和我们不在一个维度

### 6. 真正的竞争对手分析

**AHF 的优势不是"技术指标更好"，而是：**
1. **多数据源**：我们只有价格+成交量，AHF有财报+新闻+情绪
2. **LLM推理**：可以理解"美联储加息→科技股承压"这类因果关系
3. **多视角投票**：12个大师人格提供多样化的投资视角

**AHF 的劣势（真实的）：**
1. **不做实际交易**：只生成信号，没有回测/仓位管理/止损
2. **延迟高**：每个信号需要多个 LLM API 调用（成本高、速度慢）
3. **不可重现**：LLM 输出非确定性，两次运行结果不同
4. **没有风控引擎**：没有 trailing stop, pyramiding, position sizing

## 自我反思：我们做得好的和不好的

### 做得好的 ✅
1. **TDD流程建立**：34个golden threshold测试，每次改动都回归
2. **回滚纪律**：16次实验，10次失败全部正确回滚
3. **结构性问题识别**：NVDA/AMZN/CATL的warmup问题明确标记为"不可解"
4. **选股 > 交易**：这个insight非常有价值

### 做得不好的 ❌
1. **之前没有TDD**：前面10+次迭代全靠手动benchmark验证，浪费时间
2. **竞品模拟不真实**：benchmark_avg是随机模拟，不代表真实竞品
3. **没有读竞品源码**：直到老板提醒才去看AHF的真实实现
4. **信号组合方式落后**：用if/elif分支而非加权投票，失去了信号之间的信息

## 下一步行动

### 短期（可立即改进）
1. **用加权投票替代if/elif**：把 bull_signal, bear_signal, range_signal 都算一遍，加权合成
2. **添加 Bollinger Bands** 到 ranging signal
3. **重写竞品模拟**：用AHF真实逻辑（5策略加权投票）替代随机模拟

### 中期（需要研究）
4. **集成 LLM 推理**：用 Claude/GPT 作为"第6个策略"提供宏观视角
5. **多数据源**：加入 Fear & Greed Index, Put/Call Ratio 等市场情绪指标
6. **Walk-forward validation**：在不同时间窗口测试，避免过拟合

### 长期（架构改变）
7. **多资产联动信号**：BTC暴跌时，ETH/SOL的做空信号应该加强
8. **自适应策略权重**：不同市场环境自动调整5个子策略的权重
9. **真实数据回测**：用 yfinance/polygon 获取真实历史数据替代模拟
