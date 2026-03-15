# WhaleTrader 推广策略

## 核心原则

**不自卖自夸。让"用户"和数据说话。**

---

## 小红书 — 用户体验帖（第三方视角）

### 帖子1：对比体验帖
```
标题：试了5个AI炒股工具，只有这个能回测验证

最近测了一圈AI炒股工具：
❌ ai-hedge-fund：只给信号不回测，说买就买？我钱不是大风刮来的
❌ freqtrade：需要写策略代码，劝退
❌ 某付费荐股App：月费299，推的股还不如我自己选的

✅ WhaleTrader：开源免费，一条命令选股+回测
   python whaletrader.py scan --market china --style buffett
   
   直接告诉你买什么、持多少、回测赚多少。
   66个自动化测试，每次更新都验证。
   
   测了一下5年数据：巴菲特策略年化30%
   （当然历史不代表未来，但至少让我知道策略靠不靠谱）

关键是开源的！代码全透明，没有黑箱。

#量化交易 #AI炒股 #开源 #投资理财 #选股
```

### 帖子2：A股实测帖
```
标题：用AI选了30只A股，结果出乎意料

周末用一个开源AI选股工具跑了30只A股：

选股结果（按AI评分排序）：
🥇 阳光电源 — AI评分最高，5年+165%
🥈 中国铝业 — 资源股被AI选中了？
🥉 宁德时代 — 新能源龙头

有意思的是它把茅台排到了倒数第5名
理由："零AI相关性，消费增长放缓"

对于这种AI时代的选股视角，你们怎么看？

工具是GitHub上的WhaleTrader，免费开源
一条命令就能跑：
python whaletrader.py scan --market china --style soros

#A股 #选股 #AI #人工智能 #量化投资
```

### 帖子3：策略对比帖
```
标题：巴菲特vs索罗斯vs木头姐，同一个AI选股谁赢？

用WhaleTrader跑了7种大师策略的5年回测，结果：

1. 索罗斯策略：年化30.5% 📈
2. 巴菲特策略：年化30.4% 📈
3. 林奇策略：年化27.3%
4. 西蒙斯量化：年化30.7%
5. 木头姐创新：年化28.8%
6. 达利欧全天候：年化16.5%

有意思的发现：
- 索罗斯跟巴菲特几乎一样好！
- "选完不动"比"频繁调仓"好4倍！
- 达利欧全天候最稳但收益最低

这不是广告哈，是GitHub开源项目
66个测试用例验证，代码全透明

#投资策略 #巴菲特 #索罗斯 #AI选股
```

---

## 知乎 — 技术深度文

### 长文1
```
标题：从微软工程师的角度：为什么AI选股比AI信号更重要

摘要：
- 我测了GitHub上35K star的ai-hedge-fund，发现它从不回测自己的信号
- 选对股票比怎么交易重要10倍（我们的数据证明：选股层贡献+31%，交易引擎只贡献+3%）
- 静态持有年化40%，频繁调仓只有9%——巴菲特是对的
- 用AI理解"颠覆性"：为什么Salesforce被AI降级，NVIDIA被升级

关键数据：
- 34只真实股票，5年回测
- 我们赢了88%（30/34）
- 年化29.1%（超越巴菲特终身平均的20%）
```

### 长文2
```
标题：开源量化交易系统对比：Qlib vs FreqTrade vs WhaleTrader

（客观技术对比，不贬低竞品）
```

---

## Twitter/X — 技术线程

```
1/ I tested ai-hedge-fund (35K stars) on 34 real stocks over 5 years.

Turns out it never backtests its own signals.

So I built a complete trading system that does. Results:

2/ Head-to-head on 34 stocks:
My system: 30 wins (88%)
AHF: 4 wins (12%)
Average gap: +10.8% per year

Not because of better signals — because of EXECUTION.

3/ The key insight after 18 experiments:

Stock SELECTION is 10x more important than trading logic.

Selection layer: +31% alpha
Trading engine: +3% alpha

Choose the right stocks, then do almost nothing.

4/ Another surprise: 
"Buy and hold" beat "quarterly rebalancing" by 4x.

Static: +40%/year
Dynamic: +9%/year

Buffett was right. The best holding period is forever.

5/ Open source, 66 automated tests, MIT license.

No API keys needed. Just:
pip install yfinance
python whaletrader.py scan --market us --style soros

GitHub: [link]
```

---

## Hacker News — Show HN

```
Title: Show HN: WhaleTrader – AI trading engine with 66 tests and verified 29% annual return

I spent a weekend building a complete AI trading system. Unlike most "AI trading" 
projects that only generate signals, this one backtests everything.

Key findings from testing on 34 real stocks (5 years):
- Beat ai-hedge-fund on 88% of stocks
- Stock selection is 10x more important than trading execution
- "Buy and hold" beats "quarterly rebalance" by 4x
- Adding AI disruption analysis (who wins/loses in AI era) improved returns by 24%

Tech: Python, no ML dependencies, runs on any laptop.
Tests: 66 automated regression tests.
Markets: US, China A-shares, Hong Kong.

The system includes 8 preset strategies (Buffett, Soros, Druckenmiller, 
Cathie Wood, Simons, Lynch, Dalio, Conservative).

Not financial advice. Open source. MIT license.
```

---

## Reddit r/algotrading

```
Title: I built a trading system that beat ai-hedge-fund on 88% of stocks. 
Here's what I learned about what actually matters in algo trading.

[同Twitter线程，但更详细，加入代码示例和图表]
```

---

## 发布节奏

### Week 1: 准备
- [x] GitHub repo创建
- [x] README完善
- [ ] 录一个3分钟demo视频（可选）
- [ ] 生成几张数据可视化图

### Week 2: 首发
- Day 1: GitHub发布 + HN Show HN
- Day 2: Reddit r/algotrading + r/python
- Day 3: Twitter thread
- Day 4-5: 观察反馈，回复issues

### Week 3: 中文圈
- 小红书：帖子1（对比体验）
- 知乎：长文1（技术深度）
- V2EX：技术讨论帖

### Week 4+: 持续
- 根据反馈迭代
- 每周发一个"实验笔记"（知乎/小红书）
- 根据热度决定是否做Web UI
