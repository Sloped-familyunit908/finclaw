# WhaleTrader — 开源生态研究笔记

## 值得学习的开源项目

### Tier 1: 必须研究
1. **Microsoft Qlib** (16K stars) — 微软出品的AI量化平台
   - 支持ML建模 (LSTM, Transformer, TabNet)
   - RD-Agent: LLM驱动的自动因子挖掘
   - 中国A股数据集完整
   - **机会**: 老板是微软的，可以内部联系Qlib团队，或者做WhaleTrader x Qlib集成

2. **QuantStats** (5K stars) — 组合分析报告
   - Sharpe, Sortino, Calmar 等50+指标
   - 蒙特卡洛模拟
   - HTML报告导出
   - **已集成**: pip install quantstats 完成

3. **VNPy** (25K stars) — 中国量化交易框架
   - 支持CTP期货、股票接口
   - A股实盘交易接入
   - **价值**: 如果要做A股实盘，需要参考其CTP接入方式

### Tier 2: 有价值的参考
4. **Zipline** (18K stars) — Quantopian出品
   - 事件驱动回测框架（行业标准）
   - Pipeline因子系统
   - **教训**: Quantopian倒闭了——证明光有好回测不够，还要有好策略

5. **Backtrader** (15K stars) — 灵活的回测引擎
   - 策略编写比Zipline简单
   - 支持多数据源、多资产

6. **Jesse** (6K stars) — 加密货币交易机器人
   - 很好的策略DSL设计
   - 实盘+回测统一接口

7. **awesome-systematic-trading** — 策略合集
   - 40+学术论文策略（Momentum, Mean Reversion, Carry, Value等）
   - **价值**: 可以把这些策略移植到WhaleTrader的策略库

### Tier 3: 有趣但次优先
8. **Superalgos** (4K stars) — 可视化交易机器人
   - 拖拽式策略设计
   - **启发**: 未来WhaleTrader的Web UI可以参考

9. **hftbacktest** (2K stars, Rust) — 高频交易回测
   - 考虑了订单簿、队列、延迟
   - **不适用**: 我们不做高频

## 从大师策略中学到的

### 可以立即实施的改进

1. **动态再平衡周期**
   - 当前: 一次性选股，全程持有
   - 改进: 每季度重新评级，调仓
   - 参考: Dalio的全天候策略

2. **风险预算**
   - 当前: 按Grade/等权分配
   - 改进: 按"边际风险贡献"均等化 (Risk Parity)
   - 参考: 桥水的风险平价

3. **趋势强度过滤**
   - 当前: 选完就持有
   - 改进: 趋势消失时主动减仓（ATR收缩 = 减仓信号）
   - 参考: 德鲁肯米勒的"趋势不在就走人"

4. **逆向指标集成**
   - VIX (恐慌指数) — 高VIX = 巴菲特式买入机会
   - Put/Call Ratio — 极端看空 = 反转信号
   - 可以用yfinance获取: ^VIX

5. **蒙特卡洛模拟**
   - 已安装QuantStats
   - 可以对任何策略运行1000次模拟，给出概率化的收益/风险预期
   - 这比单一回测值更有说服力

## 下一步行动

### 短期 (1-2天)
- [ ] 集成QuantStats报告到CLI (`--report`标志)
- [ ] 添加季度再平衡功能
- [ ] VIX恐慌指标集成

### 中期 (1周)
- [ ] 参考Qlib的因子系统，添加ML因子
- [ ] Web UI (参考Superalgos的可视化设计)
- [ ] 实盘纸上交易 (paper trading)

### 长期 (1个月)
- [ ] A股实盘接入 (参考VNPy的CTP接口)
- [ ] 微信/Telegram推送选股信号
- [ ] Qlib x WhaleTrader集成
